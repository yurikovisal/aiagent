const ANTHROPIC_API_KEY = process.env.ANTHROPIC_API_KEY
const ANTHROPIC_MODEL = process.env.ANTHROPIC_MODEL || 'claude-haiku-4-5-20251001'

/**
 * Собирает сводку смены из транскриптов голосовых сообщений канала.
 * Без ANTHROPIC_API_KEY возвращает честный fallback — список реплик,
 * а не выдуманную сводку.
 */
export async function summarizeShift(channelName, entries) {
  if (entries.length === 0) {
    return { bullets: ['За смену сообщений ещё не было.'], generatedBy: 'none' }
  }

  if (!ANTHROPIC_API_KEY) {
    return { bullets: entries.map((e) => `${e.time} ${e.sender}: ${e.text}`), generatedBy: 'extractive' }
  }

  const transcript = entries.map((e) => `[${e.time}] ${e.sender}: ${e.text}`).join('\n')
  const prompt = `Вот голосовые сообщения смены «${channelName}» за сегодня:
${transcript}

Составь краткую сводку смены на русском: 3-6 пунктов — что сделано, что важно,
что требует внимания. Верни ТОЛЬКО JSON {"bullets": ["...", "..."]}.`

  try {
    const res = await fetch('https://api.anthropic.com/v1/messages', {
      method: 'POST',
      headers: {
        'content-type': 'application/json',
        'x-api-key': ANTHROPIC_API_KEY,
        'anthropic-version': '2023-06-01',
      },
      body: JSON.stringify({
        model: ANTHROPIC_MODEL,
        max_tokens: 500,
        messages: [{ role: 'user', content: prompt }],
      }),
    })
    if (!res.ok) throw new Error(`Anthropic API ${res.status}`)
    const data = await res.json()
    const raw = data.content?.[0]?.text?.trim() ?? '{}'
    const match = raw.match(/\{[\s\S]*\}/)
    const parsed = JSON.parse(match ? match[0] : raw)
    return { bullets: parsed.bullets ?? [], generatedBy: 'claude' }
  } catch (err) {
    console.error('[summary] failed:', err.message)
    return { bullets: entries.map((e) => `${e.time} ${e.sender}: ${e.text}`), generatedBy: 'extractive-fallback' }
  }
}
