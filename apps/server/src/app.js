import fs from 'node:fs'
import path from 'node:path'
import { fileURLToPath } from 'node:url'
import express from 'express'
import cors from 'cors'
import multer from 'multer'
import { nanoid } from 'nanoid'
import { getDb } from './db.js'
import { translateText } from './translate.js'
import { summarizeShift } from './summary.js'

const __dirname = path.dirname(fileURLToPath(import.meta.url))
const UPLOAD_DIR = path.join(__dirname, '..', 'uploads')
// На Vercel веб-клиент копируется сюда на шаге сборки (см. vercel-build в
// package.json), локально же используется собранный apps/web/dist напрямую.
const WEB_DIST_CANDIDATES = [path.join(__dirname, '..', 'public'), path.join(__dirname, '..', '..', 'web', 'dist')]
const WEB_DIST = WEB_DIST_CANDIDATES.find((p) => fs.existsSync(p))

const BLOB_TOKEN = process.env.BLOB_READ_WRITE_TOKEN
const TARGET_LANGS = { family: ['ru', 'kz'], work: ['ru', 'kz', 'en'] }

if (!BLOB_TOKEN) fs.mkdirSync(UPLOAD_DIR, { recursive: true })

const db = await getDb()

export const app = express()
app.use(cors())
app.use(express.json())

if (!BLOB_TOKEN) {
  app.use('/uploads', express.static(UPLOAD_DIR))
}
if (WEB_DIST) {
  app.use(express.static(WEB_DIST))
}

const upload = BLOB_TOKEN
  ? multer({ storage: multer.memoryStorage(), limits: { fileSize: 10 * 1024 * 1024 } })
  : multer({
      storage: multer.diskStorage({
        destination: UPLOAD_DIR,
        filename: (_req, file, cb) => cb(null, `${nanoid()}${path.extname(file.originalname) || '.webm'}`),
      }),
      limits: { fileSize: 10 * 1024 * 1024 },
    })

async function storeAudio(file) {
  if (!file) return null
  if (BLOB_TOKEN) {
    const { put } = await import('@vercel/blob')
    const blob = await put(`uploads/${nanoid()}.webm`, file.buffer, {
      access: 'public',
      token: BLOB_TOKEN,
      contentType: file.mimetype || 'audio/webm',
    })
    return blob.url
  }
  return `/uploads/${file.filename}`
}

app.get('/api/health', (_req, res) => res.json({ ok: true, storage: BLOB_TOKEN ? 'blob' : 'file' }))

app.get('/api/channels', async (_req, res) => {
  await db.read()
  const channels = db.data.channels.map((c) => ({
    ...c,
    lastMessage: [...db.data.messages].reverse().find((m) => m.channelId === c.id) ?? null,
  }))
  res.json(channels)
})

app.get('/api/channels/:id', async (req, res) => {
  await db.read()
  const channel = db.data.channels.find((c) => c.id === req.params.id)
  if (!channel) return res.status(404).json({ error: 'not_found' })
  const messages = db.data.messages.filter((m) => m.channelId === channel.id)
  res.json({ channel, messages })
})

app.post('/api/channels/:id/join', async (req, res) => {
  await db.read()
  const channel = db.data.channels.find((c) => c.id === req.params.id)
  if (!channel) return res.status(404).json({ error: 'not_found' })
  const { id, name, color } = req.body
  if (id && !channel.members.some((m) => m.id === id)) {
    channel.members.push({ id, name, color })
    await db.write()
  }
  res.json(channel)
})

app.post('/api/channels/:id/messages', upload.single('audio'), async (req, res) => {
  await db.read()
  const channel = db.data.channels.find((c) => c.id === req.params.id)
  if (!channel) return res.status(404).json({ error: 'not_found' })

  const { senderId, senderName, senderColor, transcript, duration, kind, text, sourceLang } = req.body
  const message = {
    id: nanoid(),
    channelId: channel.id,
    senderId,
    senderName,
    senderColor,
    kind: kind === 'text' ? 'text' : 'voice',
    audioUrl: await storeAudio(req.file),
    duration: duration ? Number(duration) : null,
    text: kind === 'text' ? (text ?? '') : '',
    transcript: transcript || null,
    translations: {},
    createdAt: new Date().toISOString(),
  }
  db.data.messages.push(message)
  await db.write()
  res.status(201).json(message)

  const sourceText = message.kind === 'text' ? message.text : message.transcript
  const targets = (TARGET_LANGS[channel.type] ?? ['ru']).filter((l) => l !== (sourceLang || 'ru'))
  if (sourceText && targets.length > 0) {
    const translations = await translateText(sourceText, targets)
    await db.read()
    const stored = db.data.messages.find((m) => m.id === message.id)
    if (stored) {
      stored.translations = translations
      await db.write()
    }
  }
})

app.post('/api/channels/:id/summary', async (req, res) => {
  await db.read()
  const channel = db.data.channels.find((c) => c.id === req.params.id)
  if (!channel) return res.status(404).json({ error: 'not_found' })

  const entries = db.data.messages
    .filter((m) => m.channelId === channel.id && (m.transcript || m.text))
    .map((m) => ({
      sender: m.senderName,
      time: new Date(m.createdAt).toLocaleTimeString('ru-RU', { hour: '2-digit', minute: '2-digit' }),
      text: m.transcript || m.text,
    }))

  const summary = await summarizeShift(channel.name, entries)
  const record = { id: nanoid(), channelId: channel.id, ...summary, createdAt: new Date().toISOString() }
  db.data.summaries ??= []
  db.data.summaries.push(record)
  await db.write()
  res.status(201).json(record)
})

app.get('/api/channels/:id/summaries', async (req, res) => {
  await db.read()
  res.json((db.data.summaries ?? []).filter((s) => s.channelId === req.params.id))
})
