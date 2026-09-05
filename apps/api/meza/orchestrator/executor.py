"""Tool executor: enforces RBAC permission, tool risk / approval gating, execution budget,
and writes tool_calls + audit_log for every call (§23/§24/§27/§30)."""

from __future__ import annotations

import time

from sqlalchemy.ext.asyncio import AsyncSession

from meza.core.rbac import has_permission
from meza.core.utils import new_id, utcnow
from meza.models import ToolCall
from meza.services import audit as audit_svc
from meza.tools.base import APPROVAL_REQUIRED_RISKS, ToolContext, ToolResult
from meza.tools.registry import get_tool


class Budget:
    """Per-run execution budget (§30) — prevents infinite agent loops."""

    def __init__(self, max_steps: int, max_tool_calls: int, max_handoffs: int):
        self.max_steps = max_steps
        self.max_tool_calls = max_tool_calls
        self.max_handoffs = max_handoffs
        self.steps = 0
        self.tool_calls = 0
        self.handoffs = 0

    def check_tool_call(self) -> bool:
        return self.tool_calls < self.max_tool_calls

    def check_step(self) -> bool:
        return self.steps < self.max_steps

    def check_handoff(self) -> bool:
        return self.handoffs < self.max_handoffs


async def execute_tool(
    db: AsyncSession,
    *,
    tool_name: str,
    params: dict,
    ctx: ToolContext,
    budget: Budget,
) -> ToolResult:
    tool = get_tool(tool_name)
    if not tool:
        return ToolResult(ok=False, error=f"Инструмент '{tool_name}' не найден.")
    if tool.required_permission and not has_permission(ctx.role, tool.required_permission):
        result = ToolResult(ok=False, error=f"Недостаточно прав для вызова '{tool_name}'.")
        await audit_svc.record(
            db, action="tool_call_denied", user_id=ctx.user_id, agent=ctx.agent_id, tool=tool_name,
            parameters=params, result={"error": result.error}, execution_status="DENIED",
            entity_type="tool", entity_id=tool_name,
        )
        return result
    if not budget.check_tool_call():
        return ToolResult(ok=False, error="Превышен лимит вызовов инструментов для этого запроса.")
    budget.tool_calls += 1

    started = time.perf_counter()
    call_row = ToolCall(
        run_id=ctx.run_id, agent_id=ctx.agent_id, tool_name=tool_name, risk=tool.risk.value,
        parameters=params, started_at=utcnow(), status="SUCCESS",
    )
    try:
        result = await tool.run(ctx, **params)
    except Exception as exc:  # noqa: BLE001
        duration_ms = int((time.perf_counter() - started) * 1000)
        call_row.status = "FAILED"
        call_row.error = str(exc)
        call_row.duration_ms = duration_ms
        db.add(call_row)
        await db.flush()
        await audit_svc.record(
            db, action="tool_call_failed", user_id=ctx.user_id, agent=ctx.agent_id, tool=tool_name,
            parameters=params, result={"error": str(exc)}, execution_status="FAILED", duration_ms=duration_ms,
        )
        return ToolResult(ok=False, error=f"Инструмент '{tool_name}' завершился с ошибкой: {exc}")

    duration_ms = int((time.perf_counter() - started) * 1000)
    call_row.duration_ms = duration_ms
    call_row.result_summary = (result.summary or "")[:2000]
    if result.pending_approval_id:
        call_row.status = "PENDING_APPROVAL"
        call_row.approval_id = result.pending_approval_id
    elif not result.ok:
        call_row.status = "FAILED"
        call_row.error = result.error
    db.add(call_row)
    await db.flush()
    await audit_svc.record(
        db, action="tool_call", user_id=ctx.user_id, agent=ctx.agent_id, tool=tool_name,
        parameters=params, result={"summary": result.summary, "ok": result.ok}, duration_ms=duration_ms,
        execution_status=call_row.status,
    )
    return result
