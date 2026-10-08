type SpeechRecognitionLike = {
  lang: string
  continuous: boolean
  interimResults: boolean
  onresult: ((event: any) => void) | null
  onerror: ((event: any) => void) | null
  start: () => void
  stop: () => void
}

/**
 * Живая транскрипция через Web Speech API прямо в браузере — бесплатно,
 * без ключей и без отправки аудио на сервер. Поддерживается в Chrome/Edge
 * на iOS и Android; в Safari недоступна — в этом случае возвращает null,
 * и сообщение отправляется просто как аудио, без транскрипта.
 */
export function createRecognizer(lang: string, onResult: (text: string) => void) {
  const SpeechRecognitionCtor: (new () => SpeechRecognitionLike) | undefined =
    (window as any).SpeechRecognition || (window as any).webkitSpeechRecognition
  if (!SpeechRecognitionCtor) return null

  const recognition = new SpeechRecognitionCtor()
  recognition.lang = lang
  recognition.continuous = true
  recognition.interimResults = true

  let finalText = ''
  recognition.onresult = (event: any) => {
    let interim = ''
    for (let i = event.resultIndex; i < event.results.length; i++) {
      const transcript = event.results[i][0].transcript
      if (event.results[i].isFinal) finalText += transcript + ' '
      else interim += transcript
    }
    onResult((finalText + interim).trim())
  }
  recognition.onerror = () => {}

  return {
    start: () => recognition.start(),
    stop: () => recognition.stop(),
    getFinalText: () => finalText.trim(),
  }
}
