import type { CapacitorConfig } from '@capacitor/cli'

// Приложение открывает бэкенд напрямую по сети, а не бандл из webDir —
// 10.0.2.2 — это алиас хоста для Android-эмулятора (сам эмулятор видит
// localhost хост-машины под этим адресом). Для реального устройства
// используется задеплоенный на Vercel apps/server (HTTPS, без cleartext).
const SERVER_URL = process.env.RATSIYA_SERVER_URL ?? 'http://10.0.2.2:8787'

const config: CapacitorConfig = {
  appId: 'kz.monqlab.ratsiya',
  appName: 'Рация',
  webDir: 'dist',
  server: {
    url: SERVER_URL,
    cleartext: !SERVER_URL.startsWith('https://'),
  },
}

export default config
