import type { CapacitorConfig } from '@capacitor/cli'

// В debug-сборке приложение открывает бэкенд напрямую по сети, а не бандл
// из webDir — так Socket.IO/REST работают без лишней настройки.
// 10.0.2.2 — это алиас хоста для Android-эмулятора (сам эмулятор видит
// localhost хост-машины под этим адресом). Для реального устройства или
// релизной сборки замените на адрес задеплоенного apps/server (и уберите
// cleartext, если он будет за HTTPS).
const DEV_SERVER_URL = process.env.RATSIYA_SERVER_URL ?? 'http://10.0.2.2:8787'

const config: CapacitorConfig = {
  appId: 'kz.monqlab.ratsiya',
  appName: 'Рация',
  webDir: 'dist',
  server: {
    url: DEV_SERVER_URL,
    cleartext: true,
  },
}

export default config
