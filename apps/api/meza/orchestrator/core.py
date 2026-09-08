"""MEZA Orchestrator (§3/§28/§29). The single entry point between the user and the specialized
agents. Classifies intent, routes to domains, runs independent agents in parallel, merges their
structured results, and produces one synthesized answer with visible evidence.

Specialized agents never talk to the user directly — only MEZA does (§3).
"""

from __future__ import annotations

import asyncio
import re
from collections.abc import AsyncIterator
from dataclasses import dataclass, field

from sqlalchemy.ext.asyncio import AsyncSession

from meza.agents.base import AgentResult
from meza.agents.registry import DOMAIN_TO_AGENT, get_agent
from meza.core.config import get_settings
from meza.core.db import session_scope
from meza.core.utils import new_id, utcnow
from meza.llm.factory import get_llm_provider
from meza.models import AgentRun, LLMCall
from meza.orchestrator.executor import Budget
from meza.orchestrator.router import classify_intent, route_domains
from meza.rules.scoring import dedupe
from meza.tools.base import ToolContext

STATUS_LABELS = {
    "sales": "Проверяю сделки...",
    "production": "Анализирую производство...",
    "warehouse": "Проверяю склад...",
    "procurement": "Сопоставляю закупки...",
    "finance": "Проверяю финансы...",
    "projects": "Проверяю сроки задач...",
    "documents": "Ищу документы...",
    "tenders": "Проверяю тендеры...",
    "marketing": "Проверяю маркетинг...",
    "hr": "Проверяю загрузку подразделений...",
    "analytics": "Сопоставляю данные по доменам...",
}


@dataclass
class OrchestrationResult:
    run_id: str
    status: str
    summary: str
    risks: list[dict] = field(default_factory=list)
    findings: list[dict] = field(default_factory=list)
    recommendations: list[str] = field(default_factory=list)
    actions_proposed: list[dict] = field(default_factory=list)
    sources: list[dict] = field(default_factory=list)
    per_domain: dict[str, dict] = field(default_factory=dict)
    confidence: float = 1.0
    confidence_label: str = "Высокая уверенность"

    def as_dict(self) -> dict:
        return {
            "run_id": self.run_id, "status": self.status, "summary": self.summary,
            "risks": self.risks, "findings": self.findings, "recommendations": self.recommendations,
            "actions_proposed": self.actions_proposed, "sources": self.sources,
            "per_domain": self.per_domain, "confidence": self.confidence, "confidence_label": self.confidence_label,
        }


def confidence_label(score: float) -> str:
    if score >= 0.85:
        return "Высокая уверенность"
    if score >= 0.6:
        return "Средняя уверенность"
    return "Низкая уверенность"


def _extract_order_number(text: str) -> str | None:
    m = re.search(r"\b([A-ZА-Я]{2,4}-\d{2,6})\b", text.upper())
    return m.group(1) if m else None


async def _run_domain(domain: str, user_id: int | None, role: str, run_id: str, request: str, params: dict) -> tuple[str, AgentResult]:
    """Runs one domain agent to completion, in its OWN database session.

    Agents are fanned out with asyncio.gather (§29), and SQLAlchemy's AsyncSession is not safe
    for concurrent use from multiple coroutines — sharing one session across parallel agent tasks
    causes flush/commit races (and can hang the whole request). Each parallel branch therefore
    gets its own session_scope(), committed independently; the parent orchestration run (the
    AgentRun bookkeeping row) lives in the caller's session and is finalized after all branches
    have committed their own tool_calls/audit_log/risk rows.
    """
    agent_id = DOMAIN_TO_AGENT.get(domain, domain)
    agent = get_agent(agent_id)
    if not agent:
        return domain, AgentResult(status="error", summary=f"Агент для домена '{domain}' не найден.", error="agent_missing")
    settings = get_settings()
    # Each domain agent gets its own slice of the per-request budget (§30): the orchestrator's
    # own bookkeeping (routing, synthesis) doesn't call tools, so the full configured budget is
    # available to whichever agent(s) actually do the work.
    budget = Budget(settings.max_agent_steps, settings.max_agent_tool_calls, settings.max_agent_handoffs)
    try:
        async with session_scope() as domain_db:
            agent_ctx = ToolContext(db=domain_db, user_id=user_id, role=role, run_id=run_id, agent_id=agent_id)
            result = await asyncio.wait_for(agent.handle(agent_ctx, request, params, budget), timeout=agent.timeout_seconds)
    except TimeoutError:
        result = AgentResult(status="error", summary=f"Агент {agent.name} превысил лимит времени.", error="timeout")
    except Exception as exc:  # noqa: BLE001
        result = AgentResult(status="error", summary=f"Ошибка агента {agent.name}: {exc}", error=str(exc))
    return domain, result


async def synthesize(
    request: str, domain_results: dict[str, AgentResult], run_id: str, history: list[dict] | None = None,
) -> tuple[str, float, dict | None]:
    """Turn the merged structured results into one short executive-style answer.
    Uses the local LLM if available; falls back to a deterministic summary otherwise —
    the system must never go blank just because the LLM is unreachable (§63).

    `history` (Conversation Memory, §26) is prior turns in the same conversation — it may help
    interpret a follow-up ("а по нему на складе?"), but it is never a source of facts. Every
    number in the answer still comes only from `domain_results`, which is itself assembled from
    tool calls against the live DB.
    """
    successful = {d: r for d, r in domain_results.items() if r.status == "success"}
    if not successful:
        return "Недостаточно данных для ответа. " + "; ".join(r.summary for r in domain_results.values() if r.summary), 0.3, None

    settings = get_settings()
    provider = get_llm_provider()
    context_lines = []
    for domain, r in successful.items():
        context_lines.append(f"[{domain}] {r.summary}")
        for risk in r.risks[:3]:
            context_lines.append(f"  риск: {risk.get('title')}")
    context_text = "\n".join(context_lines)

    if provider is None:
        text = " ".join(r.summary for r in successful.values())
        return text, 0.7, None

    llm_call_record = None
    try:
        messages = [
            {"role": "system", "content": (
                "Ты — MEZA, внутренний AI операционной системы ATON+. Отвечай кратко и по делу на "
                "русском языке, только на основе предоставленных фактов. Не придумывай данные, которых нет "
                "в контексте. Если данных недостаточно — так и скажи. Предыдущие реплики диалога (если есть) "
                "помогают понять, о чём именно спрашивает пользователь, но сами по себе не источник фактов."
            )},
        ]
        for turn in (history or [])[-6:]:
            messages.append({"role": turn["role"] if turn["role"] in ("user", "assistant") else "user", "content": turn["content"]})
        messages.append({"role": "user", "content": f"Вопрос: {request}\n\nДанные от агентов:\n{context_text}\n\nСформулируй краткий executive-ответ (3-6 предложений)."})
        resp = await provider.chat(messages, model=settings.effective_model, temperature=0.2)
        llm_call_record = {
            "provider": provider.name, "model": resp.model, "prompt_tokens": resp.usage.prompt_tokens,
            "completion_tokens": resp.usage.completion_tokens, "generation_ms": resp.usage.generation_ms,
            "tokens_per_sec": resp.usage.tokens_per_sec,
        }
        text = resp.text.strip() or " ".join(r.summary for r in successful.values())
        if _denies_available_data(text):
            # A small local model will occasionally claim "I don't have access to that data" or
            # "insufficient data" in its free-text synthesis even though `successful` — the
            # agents' own tool-grounded results — proves otherwise. This mirrors the per-agent
            # reasoning-loop grounding fix (ADR 0005): never let the LLM's own phrasing override
            # what the tools actually returned (§9/§66). Fall back to the deterministic join.
            text = " ".join(r.summary for r in successful.values())
            return text, 0.65, llm_call_record
        return text, 0.9, llm_call_record
    except Exception:  # noqa: BLE001
        text = " ".join(r.summary for r in successful.values())
        return text + " (LLM недоступна — использован детерминированный ответ.)", 0.6, llm_call_record


_DENIAL_PHRASES = (
    "не могу предоставить", "нет доступа", "не имею доступа", "недостаточно данных",
    "не располагаю данными", "у меня нет информации", "не могу получить доступ",
    "не могу предоставить информацию",
)


def _denies_available_data(text: str) -> bool:
    lowered = text.lower()
    return any(phrase in lowered for phrase in _DENIAL_PHRASES)


async def run_orchestration(
    db: AsyncSession,
    *,
    request: str,
    user_id: int | None,
    role: str,
    conversation_id: int | None = None,
    history: list[dict] | None = None,
    status_cb=None,
) -> OrchestrationResult:
    settings = get_settings()
    run_id = new_id()
    run = AgentRun(
        run_id=run_id, user_id=user_id, conversation_id=conversation_id, agent_id="meza",
        intent=classify_intent(request), request=request, status="RUNNING", started_at=utcnow(),
    )
    db.add(run)
    await db.flush()

    domains = route_domains(request)
    order_number = _extract_order_number(request)
    params = {"order_number": order_number} if order_number else {}

    if status_cb:
        await status_cb({"type": "status", "message": "Определяю нужные источники данных..."})

    tasks = []
    for domain in domains:
        if status_cb:
            await status_cb({"type": "status", "message": STATUS_LABELS.get(domain, f"Проверяю {domain}...")})
        tasks.append(_run_domain(domain, user_id, role, run_id, request, params))
    results = await asyncio.gather(*tasks)
    domain_results: dict[str, AgentResult] = dict(results)

    if status_cb:
        await status_cb({"type": "status", "message": "Формирую вывод..."})

    all_risks = dedupe([r for res in domain_results.values() for r in res.risks])
    all_findings = [f for res in domain_results.values() for f in res.findings]
    all_recs = [r for res in domain_results.values() for r in res.recommendations]
    all_actions = [a for res in domain_results.values() for a in res.actions_proposed]
    all_sources = [s for res in domain_results.values() for s in res.sources]

    summary_text, conf, llm_meta = await synthesize(request, domain_results, run_id, history)

    overall_status = "success" if any(r.status == "success" for r in domain_results.values()) else "partial"
    if all(r.status == "insufficient_data" for r in domain_results.values()):
        overall_status = "insufficient_data"

    run.status = "SUCCESS" if overall_status == "success" else "PARTIAL"
    run.finished_at = utcnow()
    run.duration_ms = int((run.finished_at - run.started_at).total_seconds() * 1000)
    run.steps = len(domains)
    run.confidence = conf
    run.result = {"summary": summary_text, "risks_count": len(all_risks)}
    if llm_meta:
        run.llm_calls = 1
        run.llm_tokens_in = llm_meta["prompt_tokens"]
        run.llm_tokens_out = llm_meta["completion_tokens"]
        db.add(LLMCall(
            run_id=run_id, agent_id="meza", provider=llm_meta["provider"], model=llm_meta["model"],
            purpose="synthesis", prompt_tokens=llm_meta["prompt_tokens"], completion_tokens=llm_meta["completion_tokens"],
            generation_ms=llm_meta["generation_ms"], tokens_per_sec=llm_meta["tokens_per_sec"], status="SUCCESS",
            created_at=utcnow(),
        ))
    # count tool calls performed across all agents in this run
    from sqlalchemy import func, select as sa_select
    from meza.models import ToolCall
    tc_count = (await db.execute(sa_select(func.count(ToolCall.id)).where(ToolCall.run_id == run_id))).scalar_one()
    run.tool_calls_count = tc_count
    await db.flush()

    if status_cb:
        await status_cb({"type": "done"})

    return OrchestrationResult(
        run_id=run_id, status=overall_status, summary=summary_text, risks=all_risks,
        findings=all_findings, recommendations=list(dict.fromkeys(all_recs)), actions_proposed=all_actions,
        sources=all_sources, per_domain={d: r.as_dict() for d, r in domain_results.items()},
        confidence=conf, confidence_label=confidence_label(conf),
    )
