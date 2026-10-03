import type { Identity } from '../types'

const KEY = 'ratsiya:identity'
const COLORS = ['#f97316', '#3b82f6', '#22c55e', '#ec4899', '#a855f7', '#eab308']

export function loadIdentity(): Identity | null {
  const raw = localStorage.getItem(KEY)
  return raw ? (JSON.parse(raw) as Identity) : null
}

export function saveIdentity(name: string): Identity {
  const identity: Identity = {
    id: crypto.randomUUID(),
    name,
    color: COLORS[Math.floor(Math.random() * COLORS.length)],
  }
  localStorage.setItem(KEY, JSON.stringify(identity))
  return identity
}
