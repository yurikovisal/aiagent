# aiagent

Персональный ИИ-агент на [eve](https://eve.dev/docs) с Web Chat (Next.js).

## Что внутри

- `agent/` — filesystem-first агент: instructions, tools, skills, channels
- `app/` — Web Chat UI на Next.js + AI Elements
- модель по умолчанию: `anthropic/claude-sonnet-4.6` через Vercel AI Gateway

## Требования

- Node.js 24+
- credential для модели: `AI_GATEWAY_API_KEY` или `vercel link` + OIDC

## Быстрый старт

```bash
npm install
cp .env.example .env.local
# вставь AI_GATEWAY_API_KEY в .env.local

# Web Chat (Next.js)
npm run dev

# eve TUI / HTTP API агента (по умолчанию :2000)
npm run dev:eve
```

Web Chat: [http://localhost:3000](http://localhost:3000)  
eve API: `POST http://127.0.0.1:2000/eve/v1/session`

## Структура агента

| Путь | Назначение |
| --- | --- |
| `agent/agent.ts` | модель и runtime-конфиг |
| `agent/instructions.md` | всегда-on system prompt |
| `agent/tools/` | typed tools (`defineTool`) |
| `agent/skills/` | on-demand процедуры (`load_skill`) |
| `agent/channels/eve.ts` | HTTP channel + auth |

## Полезные команды

```bash
npm run typecheck
npm run build
npm exec -- eve registry search <query>
npm exec -- eve add channel/slack
```

## Дальше

1. Уточни purpose в `agent/instructions.md`
2. Добавь tools под свои API
3. Подключи Slack/GitHub через `eve add` и Vercel Connect
4. Задеплой на Vercel
