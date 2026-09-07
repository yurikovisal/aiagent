"""Generic ReAct-style reasoning loop shared by every agent (§10/§28).

Why this exists: earlier, each agent only ever called one or two hard-coded tools with
whatever parameters the router could pull out with a regex (basically just an order number).
A free-text request like "проверь наличие трубы 40x40x2, нужно 1800 кг к 8 сентября" never
reached the availability calculation because nothing extracted "1800", "40x40x2" and the date
out of the sentence. This module lets the local LLM do that interpretation step — decide which
tool(s) to call and with what parameters — while keeping the actual facts and numbers coming
only from tool results, never from the model's own claims (§9/§66/§73: MEZA must not invent
data). The model's free text only ever supplies phrasing (summary) and recommendations; every
number, source, and status in the returned AgentResult is assembled from ToolResult objects.

Loop:
    1. Ask the LLM (JSON-schema constrained) for the next action: call a tool, or finish.
    2. If it calls a tool, run it through the normal executor (RBAC + budget + audit already
       enforced there) and feed the observation back.
    3. If it finishes (or the budget/step cap is hit), stop and hand back what was gathered.

If the LLM is unreachable, returns garbage JSON repeatedly, or gathers nothing, this returns
None and the caller falls back to the agent's own deterministic logic — the system must never
go blank just because the LLM had a bad day (§63).
"""

from __future__ import annotations

import json
import logging

from meza.agents.base import AgentResult
from meza.core.config import get_settings
from meza.core.utils import jsonable
from meza.llm.factory import get_llm_provider
from meza.orchestrator.executor import Budget, execute_tool
from meza.tools.base import ToolContext
from meza.tools.registry import get_tool

logger = logging.getLogger("meza.reasoning")

ACTION_SCHEMA = {
    "type": "object",
    "properties": {
        "thought": {"type": "string", "description": "Краткое рассуждение (не показывается пользователю)."},
        "action": {"type": "string", "enum": ["call_tool", "finish"]},
        "tool": {"type": "string", "description": "Имя инструмента, если action=call_tool."},
        "params": {"type": "object", "description": "Параметры инструмента, извлечённые из запроса."},
        "summary": {"type": "string", "description": "Краткий ответ пользователю, если action=finish."},
        "recommendations": {"type": "array", "items": {"type": "string"}},
    },
    "required": ["action"],
}

MAX_REASONING_STEPS = 5
MAX_OBSERVATION_CHARS = 1500
CARRY_OVER_KEYS = {
    "material_sku", "material_name", "order_number", "order_id", "supplier_id", "supplier_name",
    "department_id", "tender_id", "customer_id", "needed_by",
}


def _tool_manifest_text(tool_names: list[str]) -> str:
    lines = []
    for name in tool_names:
        tool = get_tool(name)
        if not tool:
            continue
        lines.append(f"- {tool.name}: {tool.description} | входные параметры (JSON schema): {json.dumps(tool.input_schema, ensure_ascii=False)}")
    return "\n".join(lines)


EXAMPLE_TOOL_CALL = (
    '{"thought": "нужно проверить остаток материала", "action": "call_tool", '
    '"tool": "get_inventory", "params": {"material_name": "Труба 40x40x2"}}'
)
EXAMPLE_FINISH = (
    '{"action": "finish", "summary": "На складе 700 кг, минимум 500 кг — дефицита нет.", '
    '"recommendations": []}'
)


def _system_prompt(agent_name: str, agent_description: str, tool_names: list[str]) -> str:
    return (
        f"Ты — {agent_name}, специализированный агент внутренней AI-системы ATON+ (MEZA). "
        f"{agent_description}\n\n"
        "Тебе доступны следующие инструменты (вызывай только их, ничего не выдумывай):\n"
        f"{_tool_manifest_text(tool_names)}\n\n"
        "Правила:\n"
        "1. На каждом шаге отвечай СТРОГО JSON-объектом по заданной схеме, без пояснений вне JSON.\n"
        "2. ЗАПРЕЩЕНО отвечать (action=finish) с числами, остатками, датами или выводами, "
        "которые не были получены из результата вызова инструмента. Если ты ещё не вызвал ни "
        "одного инструмента — ты ОБЯЗАН сначала вызвать подходящий (action=call_tool), а не "
        "гадать ответ.\n"
        "3. Извлекай параметры инструментов (числа, даты в формате YYYY-MM-DD, названия) "
        "непосредственно из запроса пользователя.\n"
        "4. Если данных не хватает для конкретных параметров — не выдумывай их, вызови "
        "инструмент с тем, что известно.\n"
        "5. Как только получены данные, достаточные для ответа — заверши работу (action=finish). "
        "Не вызывай инструменты повторно без необходимости.\n"
        "6. В summary опирайся только на результаты вызванных инструментов.\n"
        "7. Если один инструмент вычислил число (например, размер дефицита), а следующий "
        "инструмент требует это число как параметр — бери его ИЗ РЕЗУЛЬТАТА предыдущего вызова, "
        "а не из исходной формулировки запроса пользователя.\n\n"
        f"Пример вызова инструмента: {EXAMPLE_TOOL_CALL}\n"
        f"Пример завершения после того, как инструмент уже вызван и дал результат: {EXAMPLE_FINISH}\n\n"
        "Важный пример цепочки (правило 7): check_material_availability вернул "
        '{"required": 1800, "on_hand": 700, "shortage_after_incoming": 1100}. Пользователь просил '
        "1800 кг, но дефицит — только 1100 кг (часть уже есть на складе). Правильный следующий вызов: "
        '{"action": "call_tool", "tool": "create_purchase_request", '
        '"params": {"quantity": 1100, ...}} — используй 1100 (shortage_after_incoming), НЕ 1800.'
    )


def _truncate(data) -> object:
    try:
        text = json.dumps(jsonable(data), ensure_ascii=False, default=str)
    except (TypeError, ValueError):
        text = str(data)
    if len(text) > MAX_OBSERVATION_CHARS:
        text = text[:MAX_OBSERVATION_CHARS] + "...(обрезано)"
    return text


async def run_reasoning_agent(
    *,
    agent_name: str,
    agent_description: str,
    allowed_tools: list[str],
    ctx: ToolContext,
    budget: Budget,
    request: str,
    params_hint: dict | None = None,
) -> AgentResult | None:
    provider = get_llm_provider()
    if provider is None or not allowed_tools:
        return None

    settings = get_settings()
    transcript = [
        {"role": "system", "content": _system_prompt(agent_name, agent_description, allowed_tools)},
        {"role": "user", "content": (
            f"Запрос пользователя: {request}"
            + (f"\nУже известные параметры: {json.dumps(params_hint, ensure_ascii=False)}" if params_hint else "")
        )},
    ]

    collected: list[tuple[str, dict, object]] = []
    final_summary: str | None = None
    final_recs: list[str] = []
    # Short-term working memory: entity identifiers established by earlier tool calls in THIS
    # trajectory, carried forward into later ones. Small local models reliably name the right
    # tool next but sometimes drop a parameter (e.g. the material) they already established two
    # steps ago — this is not new information, just context loss, so auto-filling it is safe.
    known_entities: dict[str, object] = dict(params_hint or {})
    seen_calls: set[tuple[str, str]] = set()

    for _step in range(MAX_REASONING_STEPS):
        if not budget.check_step():
            break
        budget.steps += 1
        try:
            action, _resp = await provider.chat_json(transcript, ACTION_SCHEMA, model=settings.effective_model, temperature=0.1)
        except Exception as exc:  # noqa: BLE001
            logger.info("reasoning step failed to parse LLM output: %s", exc)
            break

        if action.get("action") == "call_tool" and action.get("tool"):
            tool_name = action["tool"]
            call_params = dict(action.get("params") or {})
            tool_obj = get_tool(tool_name)
            if tool_obj:
                for key, value in known_entities.items():
                    if key in tool_obj.input_schema.get("properties", {}) and key not in call_params and value is not None:
                        call_params[key] = value
            transcript.append({"role": "assistant", "content": json.dumps(action, ensure_ascii=False)})
            if tool_name not in allowed_tools:
                transcript.append({"role": "user", "content": (
                    f"Ошибка: инструмент '{tool_name}' недоступен этому агенту. "
                    f"Доступны только: {allowed_tools}. Выбери другой инструмент или заверши (action=finish)."
                )})
                continue
            if not budget.check_tool_call():
                transcript.append({"role": "user", "content": "Лимит вызовов инструментов исчерпан. Заверши работу (action=finish)."})
                continue
            call_key = (tool_name, json.dumps(call_params, sort_keys=True, ensure_ascii=False, default=str))
            if call_key in seen_calls:
                # Identical call already made in this trajectory — re-running it would, for a
                # WRITE tool like create_purchase_request, create a duplicate pending approval.
                # Small local models sometimes loop on a call that already succeeded instead of
                # recognizing it's done; refuse the repeat instead of re-executing it.
                transcript.append({"role": "user", "content": (
                    f"Инструмент '{tool_name}' с такими же параметрами уже был вызван в этом диалоге — "
                    "повторный вызов не выполнен. Если задача решена, заверши работу (action=finish)."
                )})
                continue
            seen_calls.add(call_key)
            known_entities.update({k: v for k, v in call_params.items() if k in CARRY_OVER_KEYS and v})
            result = await execute_tool(ctx.db, tool_name=tool_name, params=call_params, ctx=ctx, budget=budget)
            collected.append((tool_name, call_params, result))
            observation = {"ok": result.ok, "summary": result.summary, "error": result.error, "data": _truncate(result.data)}
            hint = ""
            if result.pending_approval_id:
                hint = " Действие предложено и ждёт утверждения человеком — обычно после этого нужно завершить (action=finish)."
            transcript.append({"role": "user", "content": (
                f"Результат инструмента '{tool_name}': {json.dumps(observation, ensure_ascii=False)}\n"
                f"Продолжай (call_tool) или заверши (finish), если данных достаточно для ответа.{hint}"
            )})
            continue

        if not collected:
            # Small local models sometimes try to answer straight away without calling
            # anything — that would mean inventing facts (§9/§66), which is not allowed. Force
            # at least one real tool call before any finish is accepted.
            transcript.append({"role": "assistant", "content": json.dumps(action, ensure_ascii=False)})
            transcript.append({"role": "user", "content": (
                "Ошибка: нельзя завершать работу, не вызвав ни одного инструмента — иначе ты "
                "придумываешь данные. Вызови подходящий инструмент (action=call_tool) сейчас."
            )})
            continue

        final_summary = action.get("summary") or None
        final_recs = [r for r in (action.get("recommendations") or []) if isinstance(r, str)]
        break

    if not collected:
        return None  # nothing gathered — let the caller fall back to deterministic logic

    ok_results = [r for _, _, r in collected if r.ok]
    sources = [s for _, _, r in collected for s in (r.sources or [])]
    data = {name: r.data for name, _, r in collected if r.ok and r.data is not None}
    pending_actions = [
        {"tool": name, "params": params, "pending_approval_id": r.pending_approval_id}
        for name, params, r in collected if r.pending_approval_id
    ]
    status = "success" if ok_results else "insufficient_data"
    # The summary is built from the TOOL results, never from the LLM's own "finish" text — a
    # 1.5B local model will occasionally state a conclusion that flatly contradicts what its own
    # tool calls just returned (observed: it once reported "no shortage" right after a tool call
    # had returned SHORTAGE). Facts must come from tools (§9/§66); the LLM's free text is only
    # trustworthy as phrasing when nothing more concrete is available.
    tool_summary = " ".join(r.summary for _, _, r in collected if r.summary)
    summary = tool_summary or final_summary or "Недостаточно данных для ответа."
    confidence = 0.85 if (ok_results and tool_summary) else (0.6 if ok_results else 0.4)

    return AgentResult(
        status=status,
        summary=summary,
        recommendations=final_recs,
        sources=sources,
        data=data,
        actions_proposed=pending_actions,
        confidence=confidence,
    )
