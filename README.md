# Рация

Кросс-платформенная push-to-talk рация для семьи и рабочей смены — замена
Walkie-Talkie, убранному Apple из watchOS 27. Работает в браузере на
iPhone/Android уже сегодня, с живой транскрипцией и переводом RU/KZ/EN.

## Что реализовано

- **Каналы** двух типов: «Семья» (вкладки Рация/Чат) и рабочая смена
  (вкладки Рация/Транскрипция/Сводка смены) — как на мокапе.
- **Push-to-talk**: удержание кнопки пишет голос (`MediaRecorder`),
  отпускание — мгновенно рассылает сообщение всем в канале через
  Socket.IO (реальный real-time, не поллинг).
- **Живая транскрипция** через Web Speech API прямо в браузере — бесплатно,
  без серверных затрат. Работает в Chrome/Edge на Android и iOS; в Safari
  API недоступен — в этом случае сообщение уходит просто как аудио
  (честно помечено в интерфейсе, а не подделано).
- **Перевод RU/KZ/EN** и **сводка смены** — опционально через Claude API
  (см. ниже). Без ключа приложение всё равно полностью рабочее: перевод
  помечается как недоступный, а сводка собирается как читаемый список
  реплик вместо выдуманного текста.
- **PWA**-манифест — на телефоне можно добавить на домашний экран как
  приложение.

- **Android-приложение** (`apps/web/android`) — тот же веб-клиент,
  обёрнутый через [Capacitor](https://capacitorjs.com) в настоящий
  нативный пакет `kz.monqlab.ratsiya`, а не просто ярлык на сайт.
  Собирается реальным Android Gradle-тулчейном в установленный APK
  (проверено: `./gradlew assembleDebug` проходит и даёт рабочий
  `app-debug.apk`). Разрешение на микрофон (`RECORD_AUDIO`) прописано в
  манифесте — Capacitor сам показывает системный запрос доступа при
  первом нажатии на рацию.

## Чего здесь нет — и почему

**watchOS** (настоящий компаньон для Apple Watch) собрать здесь нельзя
принципиально: нужны Xcode, macOS и Apple Developer аккаунт — это
требование платформы Apple, а не нехватка пакетов, и никакой Linux-сервер
(облачный или локальный) этого не обходит. **Wear OS**, в отличие от
watchOS, собирается тем же Android Gradle-тулчейном, что и телефонное
приложение — следующий реалистичный шаг здесь: добавить Wear OS-модуль
в `apps/web/android` (Jetpack Compose for Wear + Capacitor для
доступа к той же `apps/server` рации) без необходимости в Mac.

## Запуск

```bash
npm install
npm run dev
```

Откроется:
- веб-клиент — http://localhost:5173
- API-сервер — http://localhost:8787

Откройте приложение в двух вкладках/браузерах (или с телефона и ноутбука
в одной Wi-Fi сети) под разными именами и зайдите в один канал — рация
работает между ними в реальном времени.

### Включить реальный ИИ-перевод и сводки

```bash
cp apps/server/.env.example apps/server/.env
# впишите ANTHROPIC_API_KEY
```

## Сборка Android-приложения

Нужен Android SDK (platform-tools, `platforms;android-34`,
`build-tools;34.0.0`) и JDK 17+. Если их ещё нет — через `sdkmanager`:

```bash
sdkmanager --licenses
sdkmanager "platform-tools" "platforms;android-34" "build-tools;34.0.0"
```

Дальше:

```bash
cd apps/web
npm run build                 # собрать веб-клиент в dist/
npx cap sync android          # прокинуть конфиг/ассеты в нативный проект
cd android
echo "sdk.dir=$ANDROID_HOME" > local.properties
./gradlew assembleDebug
```

APK появится в
`apps/web/android/app/build/outputs/apk/debug/app-debug.apk`.

По умолчанию приложение смотрит на бэкенд по адресу `10.0.2.2:8787` —
это алиас хоста для Android-эмулятора (сам эмулятор видит localhost
хост-машины под этим адресом). Для реального устройства или продакшна:
задеплойте `apps/server` на публичный адрес и перед сборкой укажите
`RATSIYA_SERVER_URL=https://ваш-сервер npx cap sync android` (или
поправьте `apps/web/capacitor.config.ts` напрямую).

## Структура

```
apps/
  server/        Express + Socket.IO + lowdb (JSON-файл вместо БД для MVP)
  web/            React + Vite + Tailwind, PWA
  web/android/   нативный Android-проект (Capacitor), реальный APK
```
