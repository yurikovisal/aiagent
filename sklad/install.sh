#!/usr/bin/env bash
# MEZA — пилот «Склад»: одна команда поднимает модель, Open WebUI и регистрирует
# инструменты склада. Запускать на твоей машине (Mac, Apple Silicon), не в облаке.
#
# Использование:
#   chmod +x sklad/install.sh
#   ./sklad/install.sh
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
MODEL_TAG="qwen2.5:7b-instruct"
MODEL_NAME="meza-sklad"
WEBUI_PORT=8080
WEBUI_URL="http://localhost:${WEBUI_PORT}"
VENV_DIR="$HOME/.meza-webui"

echo "== 1/5: модель в Ollama =="
if ! command -v ollama >/dev/null 2>&1; then
  echo "Ollama не найдена в PATH. Установи: https://ollama.com/download" >&2
  exit 1
fi

if ! ollama list | grep -q "^${MODEL_TAG}"; then
  ollama pull "${MODEL_TAG}"
else
  echo "${MODEL_TAG} уже загружена, пропускаю pull."
fi

ollama create "${MODEL_NAME}" -f "${SCRIPT_DIR}/Modelfile.sklad"
echo "Модель ${MODEL_NAME} готова."

echo "== 2/5: Open WebUI =="
if [ ! -d "${VENV_DIR}" ]; then
  python3 -m venv "${VENV_DIR}"
fi
# shellcheck disable=SC1091
source "${VENV_DIR}/bin/activate"
pip install --quiet --upgrade pip
pip install --quiet open-webui

if ! curl -s -o /dev/null "${WEBUI_URL}"; then
  echo "Запускаю open-webui serve в фоне (лог: ${VENV_DIR}/webui.log)..."
  nohup open-webui serve --port "${WEBUI_PORT}" > "${VENV_DIR}/webui.log" 2>&1 &
  echo $! > "${VENV_DIR}/webui.pid"
  echo "Жду, пока поднимется..."
  for i in $(seq 1 30); do
    if curl -s -o /dev/null "${WEBUI_URL}"; then break; fi
    sleep 1
  done
else
  echo "Open WebUI уже отвечает на ${WEBUI_URL}."
fi

open "${WEBUI_URL}" 2>/dev/null || true

echo "== 3/5: аккаунт администратора =="
echo "Этот шаг нельзя сделать за тебя — Open WebUI требует создать первого админа через"
echo "форму в браузере (это именно форма, не API: токена для входа ещё не существует)."
echo "В открывшейся вкладке (${WEBUI_URL}) заполни email/пароль как для ЛЮБОГО локального"
echo "входа — наружу эти данные не уходят, сервис работает только на твоей машине."
echo
read -rp "Email администратора, который ты только что создал: " ADMIN_EMAIL
read -rsp "Пароль: " ADMIN_PASSWORD
echo

echo "== 4/5: регистрация инструментов склада =="
TOKEN=$(curl -s -X POST "${WEBUI_URL}/api/v1/auths/signin" \
  -H "Content-Type: application/json" \
  -d "{\"email\":\"${ADMIN_EMAIL}\",\"password\":\"${ADMIN_PASSWORD}\"}" \
  | python3 -c "import sys,json; print(json.load(sys.stdin).get('token',''))" 2>/dev/null || true)

if [ -z "${TOKEN}" ]; then
  echo "Не получилось войти через API (другая версия Open WebUI?)."
  echo "Сделай это руками по sklad/SETUP.md, разделы 3 — две минуты."
  pbcopy < "${SCRIPT_DIR}/tools/warehouse_tools.py" 2>/dev/null \
    && echo "Код инструмента уже в буфере обмена — просто Cmd+V в форме Create Tool."
  exit 0
fi

TOOL_CONTENT=$(python3 -c "import json; print(json.dumps(open('${SCRIPT_DIR}/tools/warehouse_tools.py').read()))")
CREATE_RESP=$(curl -s -X POST "${WEBUI_URL}/api/v1/tools/create" \
  -H "Authorization: Bearer ${TOKEN}" \
  -H "Content-Type: application/json" \
  -d "{\"id\":\"warehouse\",\"name\":\"MEZA — Склад\",\"content\":${TOOL_CONTENT},\"meta\":{\"description\":\"Поиск товаров, остатки, маршрут сборки заказа\"}}")

if echo "${CREATE_RESP}" | grep -q '"id"'; then
  echo "Инструмент warehouse зарегистрирован."
else
  echo "Регистрация через API не удалась (ответ: ${CREATE_RESP})."
  echo "Сделай это руками по sklad/SETUP.md, раздел 3."
  pbcopy < "${SCRIPT_DIR}/tools/warehouse_tools.py" 2>/dev/null \
    && echo "Код инструмента уже в буфере обмена — просто Cmd+V в форме Create Tool."
  exit 0
fi

echo "== 5/5: готово =="
echo "Открой ${WEBUI_URL} → Workspace → Models → ${MODEL_NAME} → включи тул 'MEZA — Склад'"
echo "(эту последнюю галку Open WebUI не даёт переключить через API — 5 секунд руками)."
echo
echo "Тестовые фразы для чата с ${MODEL_NAME}:"
echo '  - "Где лежит Автомат 16А и сколько его осталось?"'
echo '  - "Собери маршрут для заказа ORD-500"'
echo '  - "Какие товары заканчиваются?"'
