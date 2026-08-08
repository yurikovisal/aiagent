# Архитектура MEZA AI

```
Mobile (Flutter) / Web Admin (React)
            │ HTTPS + WSS
            ▼
Cloudflare Tunnel / Tailscale
            │
            ▼
┌──────────────────────────────────────────┐
│ Windows Docker Host                      │
│ traefik → meza-api → meza-worker (ARQ)   │
│   postgres16+pgvector · redis · minio    │
│   ollama/vLLM · whisper · vision · tts   │
└──────────────────────────────────────────┘
```

## Слои

- **API** — FastAPI (`backend/`), версия `/api/v1`
- **Workers** — ARQ + Redis (индексация, ASR, ingest)
- **AI-сервисы** — отдельные контейнеры в `services/`
- **Клиенты** — `mobile/` (Flutter), `web/` (React)

## Фаза 0 (текущая)

Поднимается базовый стек без GPU-моделей:

```bash
cp .env.example .env
docker compose -f docker/docker-compose.yml -f docker/docker-compose.dev.yml up --build
curl http://localhost:8000/health
```

GPU-стек (на сервере с NVIDIA):

```bash
docker compose -f docker/docker-compose.yml -f docker/docker-compose.gpu.yml up -d
```
