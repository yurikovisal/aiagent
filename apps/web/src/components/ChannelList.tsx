import type { Channel } from '../types'

export function ChannelList({ channels, onOpen }: { channels: Channel[]; onOpen: (id: string) => void }) {
  return (
    <div className="min-h-screen bg-ink pb-10">
      <header className="px-5 pb-4 pt-8">
        <h1 className="text-xl font-black tracking-tight text-white">Каналы</h1>
        <p className="text-sm text-white/40">Семья · Работа · Всегда на связи</p>
      </header>
      <div className="space-y-2 px-4">
        {channels.map((c) => (
          <button
            key={c.id}
            onClick={() => onOpen(c.id)}
            className="flex w-full items-center gap-3 rounded-2xl border border-white/5 bg-panel p-4 text-left transition hover:border-white/15"
          >
            <div className="flex h-12 w-12 shrink-0 items-center justify-center rounded-full bg-card text-2xl">{c.emoji}</div>
            <div className="min-w-0 flex-1">
              <div className="flex items-center justify-between gap-2">
                <span className="truncate font-semibold text-white">{c.name}</span>
                <span className="shrink-0 text-xs text-white/30">{c.members.length} участ.</span>
              </div>
              <p className="truncate text-sm text-white/40">
                {c.lastMessage
                  ? `${c.lastMessage.senderName}: ${c.lastMessage.kind === 'text' ? c.lastMessage.text : c.lastMessage.transcript || '🎤 голосовое'}`
                  : 'Пока нет сообщений'}
              </p>
            </div>
            <span className="text-white/20">›</span>
          </button>
        ))}
      </div>
    </div>
  )
}
