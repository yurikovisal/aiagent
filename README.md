# MEZA AI

Локальная ИИ-платформа для склада, производства, собраний и мобильного ассистента.

**Стек:** FastAPI · PostgreSQL/pgvector · Redis · MinIO · Ollama/vLLM · Flutter · React

## Статус

Фаза **1 — Ядро чата**: JWT+refresh, streaming-чат (Ollama/Qwen3 или mock), история, Langfuse (опц.), Flutter-чат.

План: [docs/MEZA_AI_PLAN.md](docs/MEZA_AI_PLAN.md) · полный: [docs/MEZA_AI_PLAN_FULL.md](docs/MEZA_AI_PLAN_FULL.md)

## Быстрый старт

```bash
cp .env.example .env
# без GPU можно сразу:
# echo LLM_MOCK=true >> .env

make up-dev
curl http://localhost:8000/health
open http://localhost:8000/docs
```

GPU-сервер:

```bash
make up-gpu
# затем: docker exec -it meza-ai-ollama-1 ollama pull qwen3:14b-instruct-q4_K_M
```

## Auth + Chat

```bash
# регистрация
curl -s http://localhost:8000/api/v1/auth/register \
  -H 'Content-Type: application/json' \
  -d '{"email":"demo@meza.local","password":"meza12345","full_name":"Demo"}'

# логин
TOKEN=$(curl -s http://localhost:8000/api/v1/auth/login \
  -H 'Content-Type: application/json' \
  -d '{"email":"demo@meza.local","password":"meza12345"}' | python3 -c 'import sys,json;print(json.load(sys.stdin)["access_token"])')

# новый чат
CONV=$(curl -s http://localhost:8000/api/v1/chat/conversations \
  -H "Authorization: Bearer $TOKEN" -H 'Content-Type: application/json' \
  -d '{"title":"Склад"}' | python3 -c 'import sys,json;print(json.load(sys.stdin)["id"])')

# сообщение (без стрима)
curl -s http://localhost:8000/api/v1/chat/conversations/$CONV/messages \
  -H "Authorization: Bearer $TOKEN" -H 'Content-Type: application/json' \
  -d '{"content":"Привет, MEZA","stream":false}'
```

## Mobile

```bash
cd mobile
flutter pub get
flutter run --dart-define=MEZA_API_BASE=http://10.0.2.2:8000
```

## Структура

```
docker/          # compose, traefik, init SQL, langfuse overlay
backend/         # FastAPI + Alembic + ARQ
services/        # asr · tts · vision · embed (заглушки)
web/             # React-админка (следующая итерация)
mobile/          # Flutter chat (фаза 1)
docs/
```

## API

| Метод | Путь | Описание |
|---|---|---|
| GET | `/health` | Статус и зависимости |
| POST | `/api/v1/auth/register` | Регистрация |
| POST | `/api/v1/auth/login` | JWT + refresh |
| POST | `/api/v1/auth/refresh` | Обновление токенов |
| GET | `/api/v1/auth/me` | Текущий пользователь |
| GET/POST | `/api/v1/chat/conversations` | История чатов |
| POST | `/api/v1/chat/conversations/{id}/messages` | Сообщение (SSE при `stream:true`) |
