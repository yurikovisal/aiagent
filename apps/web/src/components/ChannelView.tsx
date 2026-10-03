import { useEffect, useRef, useState } from 'react'
import type { Channel, Identity, Message } from '../types'
import { fetchChannel, joinChannel, sendTextMessage, sendVoiceMessage } from '../lib/api'
import { socket } from '../lib/socket'
import { PTTButton } from './PTTButton'
import { MessageItem } from './MessageItem'
import { ShiftSummaryTab } from './ShiftSummaryTab'

type Tab = 'radio' | 'chat' | 'transcript' | 'summary'

export function ChannelView({ channelId, me, onBack }: { channelId: string; me: Identity; onBack: () => void }) {
  const [channel, setChannel] = useState<Channel | null>(null)
  const [messages, setMessages] = useState<Message[]>([])
  const [tab, setTab] = useState<Tab>('radio')
  const [text, setText] = useState('')
  const listRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    let active = true
    fetchChannel(channelId).then(({ channel, messages }) => {
      if (!active) return
      setChannel(channel)
      setMessages(messages)
    })
    joinChannel(channelId, me)
    socket.emit('join', channelId)

    function onNew(m: Message) {
      if (m.channelId === channelId) setMessages((prev) => [...prev, m])
    }
    function onUpdate(patch: { id: string; translations: Message['translations'] }) {
      setMessages((prev) => prev.map((m) => (m.id === patch.id ? { ...m, translations: patch.translations } : m)))
    }
    socket.on('message:new', onNew)
    socket.on('message:update', onUpdate)
    return () => {
      active = false
      socket.emit('leave', channelId)
      socket.off('message:new', onNew)
      socket.off('message:update', onUpdate)
    }
  }, [channelId, me])

  useEffect(() => {
    listRef.current?.scrollTo({ top: listRef.current.scrollHeight, behavior: 'smooth' })
  }, [messages, tab])

  if (!channel) return <div className="min-h-screen bg-ink" />

  const isWork = channel.type === 'work'
  const tabs: { key: Tab; label: string }[] = isWork
    ? [
        { key: 'radio', label: 'Рация' },
        { key: 'transcript', label: 'Транскрипция' },
        { key: 'summary', label: 'Сводка смены' },
      ]
    : [
        { key: 'radio', label: 'Рация' },
        { key: 'chat', label: 'Чат' },
      ]

  async function handleRecorded(blob: Blob, transcript: string | null, duration: number) {
    await sendVoiceMessage(channelId, blob, {
      senderId: me.id,
      senderName: me.name,
      senderColor: me.color,
      transcript,
      duration,
    })
  }

  async function handleSendText(e: React.FormEvent) {
    e.preventDefault()
    if (!text.trim()) return
    await sendTextMessage(channelId, text.trim(), { senderId: me.id, senderName: me.name, senderColor: me.color })
    setText('')
  }

  const visibleMessages = messages.filter((m) => {
    if (tab === 'radio') return m.kind === 'voice'
    if (tab === 'chat') return m.kind === 'text'
    if (tab === 'transcript') return m.kind === 'voice' && !!m.transcript
    return true
  })

  return (
    <div className="flex min-h-screen flex-col bg-ink">
      <header className="flex items-center gap-3 border-b border-white/5 px-4 py-4">
        <button onClick={onBack} className="text-white/50">
          ‹
        </button>
        <div className="flex h-10 w-10 items-center justify-center rounded-full bg-card text-xl">{channel.emoji}</div>
        <div>
          <div className="font-semibold text-white">{channel.name}</div>
          <div className="text-xs text-white/40">{channel.members.length} участников</div>
        </div>
      </header>

      <nav className="flex gap-1 px-4 py-3">
        {tabs.map((t) => (
          <button
            key={t.key}
            onClick={() => setTab(t.key)}
            className={`rounded-full px-4 py-2 text-sm font-medium transition ${
              tab === t.key ? 'bg-white text-ink' : 'bg-panel text-white/50'
            }`}
          >
            {t.label}
          </button>
        ))}
      </nav>

      {tab === 'summary' ? (
        <ShiftSummaryTab channelId={channelId} />
      ) : (
        <>
          <div ref={listRef} className="flex-1 space-y-2 overflow-y-auto px-4 pb-4">
            {visibleMessages.length === 0 && <p className="pt-10 text-center text-sm text-white/30">Пока тихо в эфире</p>}
            {visibleMessages.map((m) => (
              <MessageItem key={m.id} message={m} isMine={m.senderId === me.id} />
            ))}
          </div>

          <div className="border-t border-white/5 p-4">
            {tab === 'chat' ? (
              <form onSubmit={handleSendText} className="flex gap-2">
                <input
                  value={text}
                  onChange={(e) => setText(e.target.value)}
                  placeholder="Сообщение…"
                  className="flex-1 rounded-xl border border-white/10 bg-card px-4 py-3 text-white outline-none focus:border-accent-from"
                />
                <button className="rounded-xl bg-gradient-to-r from-accent-from to-accent-to px-5 font-semibold text-white">→</button>
              </form>
            ) : (
              tab === 'radio' && (
                <div className="flex justify-center">
                  <PTTButton onRecorded={handleRecorded} />
                </div>
              )
            )}
          </div>
        </>
      )}
    </div>
  )
}
