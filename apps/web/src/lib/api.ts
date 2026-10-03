import type { Channel, Message, ShiftSummary } from '../types'

export async function fetchChannels(): Promise<Channel[]> {
  const res = await fetch('/api/channels')
  return res.json()
}

export async function fetchChannel(id: string): Promise<{ channel: Channel; messages: Message[] }> {
  const res = await fetch(`/api/channels/${id}`)
  return res.json()
}

export async function joinChannel(id: string, member: { id: string; name: string; color: string }) {
  await fetch(`/api/channels/${id}/join`, {
    method: 'POST',
    headers: { 'content-type': 'application/json' },
    body: JSON.stringify(member),
  })
}

export async function sendVoiceMessage(
  channelId: string,
  blob: Blob,
  meta: { senderId: string; senderName: string; senderColor: string; transcript: string | null; duration: number }
): Promise<Message> {
  const form = new FormData()
  form.append('audio', blob, 'message.webm')
  form.append('kind', 'voice')
  form.append('senderId', meta.senderId)
  form.append('senderName', meta.senderName)
  form.append('senderColor', meta.senderColor)
  form.append('duration', String(meta.duration))
  if (meta.transcript) form.append('transcript', meta.transcript)
  const res = await fetch(`/api/channels/${channelId}/messages`, { method: 'POST', body: form })
  return res.json()
}

export async function sendTextMessage(
  channelId: string,
  text: string,
  meta: { senderId: string; senderName: string; senderColor: string }
): Promise<Message> {
  const form = new FormData()
  form.append('kind', 'text')
  form.append('text', text)
  form.append('senderId', meta.senderId)
  form.append('senderName', meta.senderName)
  form.append('senderColor', meta.senderColor)
  const res = await fetch(`/api/channels/${channelId}/messages`, { method: 'POST', body: form })
  return res.json()
}

export async function generateSummary(channelId: string): Promise<ShiftSummary> {
  const res = await fetch(`/api/channels/${channelId}/summary`, { method: 'POST' })
  return res.json()
}

export async function fetchSummaries(channelId: string): Promise<ShiftSummary[]> {
  const res = await fetch(`/api/channels/${channelId}/summaries`)
  return res.json()
}
