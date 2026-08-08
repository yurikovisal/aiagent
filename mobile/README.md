# MEZA AI — Mobile (Flutter)

Flutter 3.27 / Dart 3.6 · iOS + Android.

## Фаза 1

- Login / Register
- Streaming-чат через SSE (`/api/v1/chat/...`)

## Запуск

```bash
# API должен быть доступен с эмулятора:
# Android emulator → http://10.0.2.2:8000
# iOS simulator → http://127.0.0.1:8000
flutter pub get
flutter run --dart-define=MEZA_API_BASE=http://10.0.2.2:8000
```

Структура: `lib/{core,features/auth,features/chat}`.
