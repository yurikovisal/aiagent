import { useRef, useState } from 'react'
import { createRecognizer } from '../lib/speech'

export function PTTButton({
  onRecorded,
  speechLang = 'ru-RU',
}: {
  onRecorded: (blob: Blob, transcript: string | null, duration: number) => void
  speechLang?: string
}) {
  const [recording, setRecording] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const mediaRecorderRef = useRef<MediaRecorder | null>(null)
  const chunksRef = useRef<Blob[]>([])
  const startedAtRef = useRef(0)
  const recognizerRef = useRef<ReturnType<typeof createRecognizer>>(null)
  const streamRef = useRef<MediaStream | null>(null)

  async function start() {
    setError(null)
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true })
      streamRef.current = stream

      const recorder = new MediaRecorder(stream)
      chunksRef.current = []
      recorder.ondataavailable = (e) => chunksRef.current.push(e.data)
      recorder.start()
      mediaRecorderRef.current = recorder
      startedAtRef.current = Date.now()

      recognizerRef.current = createRecognizer(speechLang, () => {})
      recognizerRef.current?.start()

      setRecording(true)
    } catch {
      setError('Нет доступа к микрофону')
    }
  }

  function stop() {
    const recorder = mediaRecorderRef.current
    if (!recorder) return
    const duration = (Date.now() - startedAtRef.current) / 1000
    recorder.onstop = () => {
      const blob = new Blob(chunksRef.current, { type: 'audio/webm' })
      const transcript = recognizerRef.current?.getFinalText() || null
      onRecorded(blob, transcript, duration)
      streamRef.current?.getTracks().forEach((t) => t.stop())
    }
    recorder.stop()
    recognizerRef.current?.stop()
    mediaRecorderRef.current = null
    setRecording(false)
  }

  return (
    <div className="flex flex-col items-center gap-2">
      <button
        onPointerDown={start}
        onPointerUp={stop}
        onPointerLeave={() => recording && stop()}
        className={`flex h-24 w-24 items-center justify-center rounded-full bg-gradient-to-br from-accent-from to-accent-to text-3xl text-white shadow-lg transition ${
          recording ? 'scale-110 shadow-[0_0_40px_rgba(247,148,29,0.6)]' : 'shadow-[0_0_20px_rgba(247,148,29,0.3)]'
        }`}
      >
        🎙️
      </button>
      <span className="text-sm font-medium text-white/70">{recording ? 'Говорите…' : 'Удерживайте для передачи'}</span>
      {error && <span className="text-xs text-red-400">{error}</span>}
    </div>
  )
}
