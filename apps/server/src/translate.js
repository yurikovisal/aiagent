const ANTHROPIC_API_KEY = process.env.ANTHROPIC_API_KEY
const ANTHROPIC_MODEL = process.env.ANTHROPIC_MODEL || 'claude-haiku-4-5-20251001'

const LANG_NAMES = { ru: 'русский', kz: 'казахский', en: 'английский' }

/**
 * Переводит текст на запрошенные языки.
 * Без ANTHROPIC_API_KEY возвращает null для каждого языка — UI показывает,
 * что перевод недоступен, вместо того чтобы молча выдавать неверный текст.
 */
export async function translateText(text, targetLangs) {
  if (!text || !text.trim() || targetLangs.length === 0) return {}

  if (!ANTHROPIC_API_KEY) {
    return Object.fromEntries(targetLangs.map((l) => [l, null]))
  }

  const wanted = targetLangs.map((l) => `"${l}" (${LANG_NAMES[l] ?? l})`).join(', ')
  const prompt = `Переведи фразу на следующие языки: ${wanted}.
Верни ТОЛЬКО JSON-объект без markdown и пояснений, вида {"ru": "...", "kz": "..."},
где ключи — это коды языков из списка выше.

Фраза: "${text}"`

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
        max_tokens: 300,
        messages: [{ role: 'user', content: prompt }],
      }),
    })
    if (!res.ok) throw new Error(`Anthropic API ${res.status}`)
    const data = await res.json()
    const raw = data.content?.[0]?.text?.trim() ?? '{}'
    const match = raw.match(/\{[\s\S]*\}/)
    return JSON.parse(match ? match[0] : raw)
  } catch (err) {
    console.error('[translate] failed:', err.message)
    return Object.fromEntries(targetLangs.map((l) => [l, null]))
  }
}
