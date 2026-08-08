# MEZA AI

Локальная ИИ-платформа для склада, производства, собраний и мобильного ассистента.

**Стек:** FastAPI · PostgreSQL/pgvector · Redis · MinIO · Ollama/vLLM · Flutter · React

## Статус

Фаза **0 — Каркас**: docker-compose, FastAPI `/health`, PG + Redis + MinIO, CI.

Дорожная карта: [docs/MEZA_AI_PLAN.md](docs/MEZA_AI_PLAN.md) · полный план: [docs/MEZA_AI_PLAN_FULL.md](docs/MEZA_AI_PLAN_FULL.md)

## Быстрый старт

```bash
cp .env.example .env
make up-dev
# или:
# docker compose -f docker/docker-compose.yml -f docker/docker-compose.dev.yml up --build
```

Проверка:

```bash
curl http://localhost:8000/health
open http://localhost:8000/docs
```

GPU-сервер (NVIDIA + WSL2):

```bash
make up-gpu
```

## Структура

```
docker/          # compose, traefik, init SQL
backend/         # FastAPI API + ARQ workers + Alembic
services/        # asr · tts · vision · embed (заглушки)
web/             # React-админка (фаза 1+)
mobile/          # Flutter (фаза 1+)
docs/            # архитектура и план
```

## Требования

- Docker Desktop / Docker Engine + Compose
- Node.js 24+ (web, позже)
- Flutter 3.27+ (mobile, позже)
- GPU: RTX 3090/4090 24 ГБ для локальных моделей (фаза 1+)

## API (фаза 0)

| Метод | Путь | Описание |
|---|---|---|
| GET | `/health` | Статус сервиса и зависимостей |
| GET | `/api/v1/*/status` | Заглушки доменов |
| GET | `/docs` | OpenAPI |
