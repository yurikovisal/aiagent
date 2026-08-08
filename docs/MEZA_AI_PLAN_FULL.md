# MEZA AI Platform — план построения

**Сервер:** Windows 11 Pro / Server 2022 + Docker Desktop (WSL2 backend) + NVIDIA GPU
**Клиенты:** iOS + Android (Flutter), Web-админка (React)
**Ядро:** FastAPI + PostgreSQL/pgvector + Redis + локальные модели (Ollama/vLLM)

---

## 1. Целевая архитектура

```
                    ┌─────────────────────────────────────────┐
                    │  Mobile: iOS / Android (Flutter)        │
                    │  чат · голос · камера · сканер · задачи │
                    └───────────────┬─────────────────────────┘
                                    │ HTTPS + WSS
                    ┌───────────────▼─────────────────────────┐
                    │  Cloudflare Tunnel / Tailscale (без     │
                    │  проброса портов, mTLS-опция)           │
                    └───────────────┬─────────────────────────┘
┌───────────────────────────────────▼──────────────────────────────────────┐
│  WINDOWS DOCKER HOST                                                      │
│                                                                            │
│  traefik ──> meza-api (FastAPI)  ──> meza-worker (ARQ/Celery)             │
│                    │                        │                              │
│      ┌─────────────┼────────────────────────┼─────────────────┐           │
│      ▼             ▼                        ▼                 ▼           │
│  postgres16     redis 7              minio (S3)          qdrant (опц.)     │
│  + pgvector   (кэш/очередь)      аудио/фото/док                           │
│                                                                            │
│  ── AI-слой (GPU) ──────────────────────────────────────────────────────  │
│  ollama/vLLM      whisper-svc        vision-svc        tts-svc      embed  │
│  Qwen3-14B     faster-whisper v3   Qwen2.5-VL-7B     Silero/XTTS   bge-m3  │
│                + pyannote 3.1      + PaddleOCR                  + reranker │
│                                                                            │
│  ── Коннекторы ────────────────────────────────────────────────────────   │
│  1С · WMS(PG) · Excel/GSheets · Bitrix24 · IMAP · Telegram · Drive ·       │
│  goszakup.gov.kz · Kaspi/Satu · вебхуки                                    │
│                                                                            │
│  ── Наблюдаемость ── prometheus · grafana · loki · langfuse                │
└────────────────────────────────────────────────────────────────────────────┘
```

---

## 2. Стек (конкретные версии)

| Слой | Технология | Зачем |
|---|---|---|
| API | Python 3.12, FastAPI 0.115, Pydantic v2, SQLAlchemy 2.0, Alembic | Совместимо с MEZA Warehouse |
| Очередь | ARQ (проще Celery) + Redis 7 | фоновые задачи: индексация, транскрипция |
| БД | PostgreSQL 16 + pgvector 0.7 + pg_trgm | гибридный поиск в одной БД |
| Объекты | MinIO | аудио собраний, фото, накладные |
| LLM | Qwen3-14B-Instruct Q4_K_M (Ollama) / vLLM AWQ | 24 ГБ VRAM, русский, tool-calling |
| VLM | Qwen2.5-VL-7B-Instruct | фото склада, МАФ, дефекты |
| OCR | PaddleOCR-v4 (ru+en) | накладные, шильдики, спецификации |
| Детекция | YOLOv11n дообученная | подсчёт позиций, СИЗ, занятость ячеек |
| ASR | faster-whisper large-v3 + WhisperX | стрим + тайминги |
| Диаризация | pyannote/speaker-diarization-3.1 | «кто что сказал» на собрании |
| TTS | Silero v4 ru (быстрый) + XTTS-v2 (клон голоса) | ответ голосом |
| Эмбеддинги | BAAI/bge-m3 | мультиязычность RU/KZ/EN |
| Реранк | BAAI/bge-reranker-v2-m3 | точность RAG +15–25 % |
| Мобильное | Flutter 3.27 / Dart 3.6 | одна база кода, отличная работа с audio/camera |
| Web-админка | React 19 + Vite + shadcn/ui | загрузка знаний, коннекторы, логи |
| Трассировка | Langfuse (self-hosted) | стоимость/качество каждого ответа |

**Железо сервера (минимум / рекомендуемо):**
RTX 3090 24 ГБ / RTX 4090 24 ГБ · 64 / 128 ГБ RAM · NVMe 2 ТБ · Ryzen 9 или i9.
GPU в Docker: WSL2 + NVIDIA Container Toolkit, `deploy.resources.reservations.devices` в compose.

---

## 3. Функциональные домены

### 3.1 Ядро RAG
Ingest → парсинг (unstructured/docling) → чанкинг (семантический, 512 токенов, overlap 64) → эмбеддинг bge-m3 → pgvector.
Поиск: BM25 (`ts_vector`) + косинус (HNSW) → RRF-слияние → реранк → топ-8 в контекст.
Обязательно: цитирование источника (документ + страница) в каждом ответе.

### 3.2 Склад
Прямая интеграция с **MEZA Warehouse** (12 моделей, миграция `0039`). LLM получает не текст, а **инструменты**:
- `stock_balance(sku, warehouse)` — остатки
- `stock_movement(sku, period)` — движения
- `deficit_forecast(days)` — прогноз дефицита по скользящему среднему + сезонность
- `inventory_diff(session_id)` — расхождения инвентаризации
- `locate_item(sku)` — где физически лежит
- `invoice_match(photo_id)` — сверка накладной с фото

### 3.3 Конвейер / производство
- План-факт по сменам, OEE (доступность × производительность × качество)
- Детекция узких мест: очередь на операции, время такта vs время цикла
- Расчёт загрузки под тендер: «успеем ли 240 позиций МАФ к 15.09»
- Инструменты: `production_plan()`, `bottleneck_analysis()`, `capacity_check(order)`

### 3.4 Собрания
Поток: запись (мобильное, фон) → чанки по 30 с в MinIO → VAD (Silero VAD) → WhisperX ru → pyannote диаризация → сшивка → LLM-конвейер из 3 шагов:
1. **Протокол** (структурированный JSON: участники, темы, тайм-коды)
2. **Решения и задачи** (кто, что, к какому сроку)
3. **Предложения** — RAG по внутренней базе: «на прошлой встрече по этому объекту решили иначе», «на складе нет 40×40, срок поставки 12 дней»

Выход: карточка встречи + автосоздание задач + пуш ответственным.

### 3.5 Зрение
Три режима:
- **Фото-вопрос**: «что это и сколько стоит» → VLM + RAG по каталогу МАФ (194 позиции, коды УСН 8.02-03)
- **Документ**: накладная/спецификация → OCR → структурирование → сверка с заказом
- **Поток с камеры**: кадры раз в 2 с → YOLO (СИЗ, занятость ячеек, посторонние) → событие в Redis → уведомление

### 3.6 Голос
Полнодуплекс через один WebSocket `/ws/voice`:
`mic 16 kHz PCM → VAD → partial ASR → финал → LLM (stream) → TTS чанками → плеер`
Целевая задержка «конец речи → первый звук ответа»: **< 1.2 с** (Silero TTS, стриминг первого предложения).
Barge-in: приход речи пользователя обрывает воспроизведение.

---

## 4. Структура монорепозитория

```
meza-ai/
├── docker/
│   ├── docker-compose.yml            # база
│   ├── docker-compose.gpu.yml        # override для GPU
│   ├── docker-compose.dev.yml
│   └── traefik/
├── backend/
│   ├── app/
│   │   ├── main.py
│   │   ├── core/           # config, security, deps, logging
│   │   ├── models/         # SQLAlchemy
│   │   ├── schemas/        # Pydantic
│   │   ├── api/v1/         # auth, chat, voice_ws, vision, warehouse,
│   │   │                   # production, meetings, connectors, admin
│   │   ├── services/
│   │   │   ├── llm/        # ollama_client, router, tools, prompts
│   │   │   ├── rag/        # ingest, chunk, embed, retrieve, rerank
│   │   │   ├── asr/  tts/  vision/
│   │   │   ├── meetings/   # pipeline, diarize, summarize
│   │   │   └── domain/     # warehouse.py, conveyor.py, tender.py
│   │   ├── connectors/     # base.py + onec, wms, excel, bitrix,
│   │   │                   # imap, telegram, gdrive, goszakup
│   │   └── workers/        # arq tasks
│   ├── alembic/
│   └── tests/
├── services/
│   ├── asr/     # FastAPI-обёртка faster-whisper + pyannote
│   ├── tts/     # Silero + XTTS
│   ├── vision/  # Qwen2.5-VL + PaddleOCR + YOLO
│   └── embed/   # bge-m3 + reranker (infinity)
├── mobile/      # Flutter
│   └── lib/{core,data,domain,features,widgets}
├── web/         # React админка
└── docs/
```

---

## 5. Схема БД (ключевые таблицы)

```
users, devices, sessions, api_keys
conversations, messages, message_citations
documents, doc_chunks(embedding vector(1024)), doc_sources
connectors, connector_runs, connector_secrets(encrypted)
meetings, meeting_segments, meeting_speakers, meeting_actions
vision_jobs, vision_detections
audio_files, media_objects
tools_calls, llm_traces(cost, latency, model)
warehouse_* (из модуля MEZA Warehouse)
production_orders, production_ops, downtime_events
```

Индексы: HNSW на `doc_chunks.embedding` (m=16, ef_construction=64), GIN на `to_tsvector('russian', text)`.

---

## 6. Дорожная карта (12 недель)

| Фаза | Недели | Результат |
|---|---|---|
| **0. Каркас** | 1 | docker-compose поднимается, FastAPI /health, PG+Redis+MinIO, GPU виден в контейнере, CI |
| **1. Ядро чата** | 2–3 | Auth (JWT+refresh), streaming-чат с Qwen3, история, Langfuse, Flutter-приложение с чатом |
| **2. RAG** | 4–5 | Загрузка PDF/DOCX/XLSX, гибридный поиск, реранк, цитаты. Загружены каталог МАФ, ГОСТы, регламенты |
| **3. Домены** | 6–7 | Tool-calling: склад + производство. Коннекторы 1С/WMS/Excel. Ответы с реальными цифрами |
| **4. Зрение** | 8–9 | Фото → VLM/OCR/YOLO, сканер штрихкодов, сверка накладных, распознавание МАФ по фото |
| **5. Голос** | 10 | WS-дуплекс, TTS-стрим, barge-in, hands-free на складе |
| **6. Собрания** | 11 | Фоновая запись, диаризация, протокол, задачи, проактивные предложения |
| **7. Продакшн** | 12 | Backup, мониторинг, нагрузочный тест, TestFlight + Google Play internal, документация |

Каждая фаза заканчивается работающим демо — не переходить дальше, пока предыдущее не используется в реальной работе.

---

## 7. Безопасность и право

- Публикация только через Cloudflare Tunnel или Tailscale — никаких проброшенных портов.
- Секреты коннекторов — шифрование Fernet, ключ в переменной окружения хоста, не в git.
- Аудио собраний: **обязательное уведомление участников и согласие** (Закон РК «О персональных данных» № 94-V), retention 90 дней, кнопка удаления.
- RBAC: роли `admin / manager / warehouse / production / viewer`, фильтрация RAG по правам на источник.
- Аудит-лог всех tool-calls, изменяющих данные (списание, приход) — с подтверждением от человека.
- Бэкап: `pg_dump` + MinIO-снапшот ежедневно на отдельный диск, еженедельно — вне офиса.

---

## 8. Критерии готовности (не размытые)

- Ответ RAG: точность на 50 контрольных вопросах ≥ 85 %, галлюцинации без цитат — 0.
- Первый токен чата < 1.5 с, полный ответ 300 токенов < 8 с.
- Голос: end-of-speech → звук < 1.2 с.
- Транскрипция ru: WER ≤ 12 % на записи реального собрания.
- Распознавание МАФ по фото: top-1 ≥ 80 % по каталогу из 194 позиций.
- Мобильное: холодный старт < 2 с, работа офлайн-очереди при потере сети.
