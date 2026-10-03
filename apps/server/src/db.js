import fs from 'node:fs'
import path from 'node:path'
import { fileURLToPath } from 'node:url'
import { JSONFilePreset } from 'lowdb/node'

const __dirname = path.dirname(fileURLToPath(import.meta.url))
const DATA_DIR = path.join(__dirname, '..', 'data')
const DB_PATH = path.join(DATA_DIR, 'db.json')

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

let dbPromise

export function getDb() {
  if (!dbPromise) {
    fs.mkdirSync(DATA_DIR, { recursive: true })
    dbPromise = JSONFilePreset(DB_PATH, defaultData)
  }
  return dbPromise
}
