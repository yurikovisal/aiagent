export type Member = { id: string; name: string; color: string }

export type Channel = {
  id: string
  name: string
  type: 'family' | 'work'
  emoji: string
  members: Member[]
  lastMessage?: Message | null
}

export type Message = {
  id: string
  channelId: string
  senderId: string
  senderName: string
  senderColor: string
  kind: 'voice' | 'text'
  audioUrl: string | null
  duration: number | null
  text: string
  transcript: string | null
  translations: Partial<Record<'ru' | 'kz' | 'en', string | null>>
  createdAt: string
}

export type ShiftSummary = {
  id: string
  channelId: string
  bullets: string[]
  generatedBy: string
  createdAt: string
}

export type Identity = { id: string; name: string; color: string }
