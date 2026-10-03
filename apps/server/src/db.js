import fs from 'node:fs'
import path from 'node:path'
import { fileURLToPath } from 'node:url'
import { JSONFilePreset } from 'lowdb/node'

const __dirname = path.dirname(fileURLToPath(import.meta.url))
const DATA_DIR = path.join(__dirname, '..', 'data')
const DB_PATH = path.join(DATA_DIR, 'db.json')
const BLOB_PATHNAME = 'ratsiya/db.json'

const defaultData = {
  channels: [
    {
      id: 'family-1',
      name: 'Семья',
      type: 'family',
      emoji: '👨‍👩‍👧',
      members: [
        { id: 'mama', name: 'Мама', color: '#f97316' },
        { id: 'alisha', name: 'Алиша', color: '#ec4899' },
        { id: 'papa', name: 'Папа', color: '#3b82f6' },
      ],
    },
    {
      id: 'work-2',
      name: 'Смена 2',
      type: 'work',
      emoji: '👷',
      members: [
        { id: 'nurlan', name: 'Нурлан', color: '#eab308' },
        { id: 'aleksey', name: 'Алексей', color: '#22c55e' },
      ],
    },
  ],
  messages: [],
  summaries: [],
}

const BLOB_TOKEN = process.env.BLOB_READ_WRITE_TOKEN

/**
 * Vercel-функции — serverless и ничего не держат на диске между вызовами,
 * поэтому там состояние читается/пишется в Vercel Blob (по одному JSON-файлу
 * на всю базу — для масштаба этого приложения read-modify-write достаточно).
 * Локально (npm run dev), без BLOB_READ_WRITE_TOKEN, используется обычный
 * JSON-файл на диске через lowdb — быстрее и не требует облачных ключей.
 */
async function createBlobDb() {
  const { put, head } = await import('@vercel/blob')

  async function fetchData() {
    try {
      const info = await head(BLOB_PATHNAME, { token: BLOB_TOKEN })
      const res = await fetch(info.url, { cache: 'no-store' })
      if (!res.ok) throw new Error(`blob fetch ${res.status}`)
      return await res.json()
    } catch {
      return null
    }
  }

  const store = {
    data: (await fetchData()) ?? structuredClone(defaultData),
    async read() {
      const fresh = await fetchData()
      if (fresh) store.data = fresh
    },
    async write() {
      await put(BLOB_PATHNAME, JSON.stringify(store.data), {
        access: 'public',
        token: BLOB_TOKEN,
        addRandomSuffix: false,
        allowOverwrite: true,
        contentType: 'application/json',
      })
    },
  }

  if (!(await fetchData())) await store.write()
  return store
}

let dbPromise

export function getDb() {
  if (!dbPromise) {
    dbPromise = BLOB_TOKEN
      ? createBlobDb()
      : (fs.mkdirSync(DATA_DIR, { recursive: true }), JSONFilePreset(DB_PATH, defaultData))
  }
  return dbPromise
}
