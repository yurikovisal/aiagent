import { useRef, useState } from 'react'
import type { Message } from '../types'
import { Waveform } from './Waveform'

const LANG_LABEL: Record<string, string> = { ru: 'RU', kz: 'KZ', en: 'EN' }

export function MessageItem({ message, isMine }: { message: Message; isMine: boolean }) {
  const audioRef = useRef<HTMLAudioElement>(null)
  const [playing, setPlaying] = useState(false)
  const [progress, setProgress] = useState(0)

  const time = new Date(message.createdAt).toLocaleTimeString('ru-RU', { hour: '2-digit', minute: '2-digit' })

  function toggle() {
    const audio = audioRef.current
    if (!audio) return
    if (playing) audio.pause()
    else audio.play()
  }

  const translations = Object.entries(message.translations || {}).filter(([, text]) => !!text)
  const hasPendingTranslation =
    message.kind === 'voice' && !!message.transcript && translations.length === 0 && message.translations
      ? Object.keys(message.translations).length === 0
      : false

  return (
    <div className="rounded-xl border border-white/5 bg-panel p-3">
      <div className="flex items-center justify-between">
        <span className="text-sm font-semibold" style={{ color: message.senderColor }}>
          {isMine ? 'Вы' : message.senderName}
        </span>
        <span className="text-xs text-white/30">{time}</span>
      </div>

      {message.kind === 'voice' ? (
        <div className="mt-2 flex items-center gap-3">
          <button
            onClick={toggle}
            className="flex h-9 w-9 shrink-0 items-center justify-center rounded-full bg-gradient-to-br from-accent-from to-accent-to text-white"
          >
            {playing ? '❚❚' : '▶'}
          </button>
          <Waveform seed={message.id} progress={progress} />
          <span className="shrink-0 text-xs text-white/30">
            {message.duration ? `0:${String(Math.round(message.duration)).padStart(2, '0')}` : ''}
          </span>
          {message.audioUrl && (
            <audio
              ref={audioRef}
              src={message.audioUrl}
              onPlay={() => setPlaying(true)}
              onPause={() => setPlaying(false)}
              onEnded={() => {
                setPlaying(false)
                setProgress(0)
              }}
              onTimeUpdate={(e) => {
                const el = e.currentTarget
                if (el.duration) setProgress(el.currentTime / el.duration)
              }}
              className="hidden"
            />
          )}
        </div>
      ) : (
        <p className="mt-1 text-white">{message.text}</p>
      )}

      {message.kind === 'voice' && !message.transcript && (
        <p className="mt-2 text-xs italic text-white/25">Транскрипция недоступна в этом браузере</p>
      )}

      {(message.transcript || message.text) && (
        <div className="mt-2 space-y-1 border-t border-white/5 pt-2">
          {message.kind === 'voice' && message.transcript && <p className="text-sm text-white/70">{message.transcript}</p>}
          {translations.map(([lang, text]) => (
            <div key={lang} className="flex items-start gap-2 text-sm text-white/50">
              <span className="mt-[2px] shrink-0 rounded border border-white/10 px-1 text-[10px] text-white/40">
                {LANG_LABEL[lang] ?? lang.toUpperCase()}
              </span>
              <span>{text}</span>
            </div>
          ))}
          {hasPendingTranslation && <p className="text-xs italic text-white/25">Перевожу…</p>}
        </div>
      )}
    </div>
  )
}
