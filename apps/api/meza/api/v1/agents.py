from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from meza.api.deps import require_permission
from meza.core.db import get_db
from meza.core.rbac import Permission
from meza.agents.registry import manifest as agents_manifest
from meza.models import AgentRun, LLMCall, ToolCall
from meza.tools.registry import manifest as tools_manifest

router = APIRouter(prefix="/api/v1/agents", tags=["agents"])


@router.get("")
async def list_agents(_=Depends(require_permission(Permission.READ_AI_OPS))):
    return agents_manifest()


@router.get("/tools")
async def list_tools(_=Depends(require_permission(Permission.READ_AI_OPS))):
    return tools_manifest()


@router.get("/runs")
async def list_runs(limit: int = 50, db: AsyncSession = Depends(get_db), _=Depends(require_permission(Permission.READ_AI_OPS))):
    rows = (await db.execute(select(AgentRun).order_by(AgentRun.started_at.desc()).limit(limit))).scalars().all()
    return [r.as_dict() for r in rows]


@router.get("/runs/{run_id}")
async def get_run(run_id: str, db: AsyncSession = Depends(get_db), _=Depends(require_permission(Permission.READ_AI_OPS))):
    run = (await db.execute(select(AgentRun).where(AgentRun.run_id == run_id))).scalars().first()
    if not run:
        return {"error": "not_found"}
    tool_calls = (await db.execute(select(ToolCall).where(ToolCall.run_id == run_id))).scalars().all()
    llm_calls = (await db.execute(select(LLMCall).where(LLMCall.run_id == run_id))).scalars().all()
    return {"run": run.as_dict(), "tool_calls": [t.as_dict() for t in tool_calls], "llm_calls": [l.as_dict() for l in llm_calls]}


@router.get("/stats")
async def stats(db: AsyncSession = Depends(get_db), _=Depends(require_permission(Permission.READ_AI_OPS))):
    total = (await db.execute(select(func.count(AgentRun.id)))).scalar_one()
    active = (await db.execute(select(func.count(AgentRun.id)).where(AgentRun.status == "RUNNING"))).scalar_one()
    failed = (await db.execute(select(func.count(AgentRun.id)).where(AgentRun.status == "FAILED"))).scalar_one()
    completed = (await db.execute(select(func.count(AgentRun.id)).where(AgentRun.status.in_(["SUCCESS", "PARTIAL"])))).scalar_one()
    avg_duration = (await db.execute(select(func.avg(AgentRun.duration_ms)).where(AgentRun.duration_ms.is_not(None)))).scalar_one()
    tool_calls_total = (await db.execute(select(func.count(ToolCall.id)))).scalar_one()
    llm_calls_total = (await db.execute(select(func.count(LLMCall.id)))).scalar_one()
    avg_tps = (await db.execute(select(func.avg(LLMCall.tokens_per_sec)).where(LLMCall.tokens_per_sec > 0))).scalar_one()
    from meza.models import Approval

    pending_approvals = (await db.execute(select(func.count(Approval.id)).where(Approval.status == "PENDING"))).scalar_one()
    return {
        "active_runs": active, "completed_runs": completed, "failed_runs": failed, "total_runs": total,
        "avg_duration_ms": round(avg_duration or 0, 1), "tool_calls_total": tool_calls_total,
        "llm_calls_total": llm_calls_total, "avg_tokens_per_sec": round(avg_tps or 0, 2),
        "pending_approvals": pending_approvals,
    }
