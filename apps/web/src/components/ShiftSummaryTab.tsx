import { useEffect, useState } from 'react'
import { fetchSummaries, generateSummary } from '../lib/api'
import type { ShiftSummary } from '../types'

export function ShiftSummaryTab({ channelId }: { channelId: string }) {
  const [summaries, setSummaries] = useState<ShiftSummary[]>([])
  const [loading, setLoading] = useState(false)

  useEffect(() => {
    fetchSummaries(channelId).then(setSummaries)
  }, [channelId])

  async function handleGenerate() {
    setLoading(true)
    try {
      const summary = await generateSummary(channelId)
      setSummaries((prev) => [...prev, summary])
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="space-y-3 p-4">
      <button
        onClick={handleGenerate}
        disabled={loading}
        className="w-full rounded-xl bg-gradient-to-r from-accent-from to-accent-to py-3 font-semibold text-white disabled:opacity-50"
      >
        {loading ? 'Собираю сводку…' : 'Сгенерировать сводку смены'}
      </button>
      {[...summaries].reverse().map((s) => (
        <div key={s.id} className="rounded-xl border border-white/5 bg-panel p-4">
          <div className="flex items-center justify-between text-xs text-white/30">
            <span>{new Date(s.createdAt).toLocaleString('ru-RU')}</span>
            <span>{s.generatedBy === 'claude' ? '✨ Claude' : 'без ИИ'}</span>
          </div>
          <ul className="mt-2 list-disc space-y-1 pl-4 text-sm text-white/80">
            {s.bullets.map((b, i) => (
              <li key={i}>{b}</li>
            ))}
          </ul>
        </div>
      ))}
      {summaries.length === 0 && <p className="text-center text-sm text-white/30">Сводок пока нет</p>}
    </div>
  )
}
