"""MEZA Executive Agent (§11.1). Synthesizes cross-department findings into the Daily Brief / 
Needs Attention view. Uses the LLM only for the final natural-language synthesis — never to 
invent facts; every risk/finding it reports came from a tool or the Risk Engine."""

from __future__ import annotations

from meza.agents.base import Agent, AgentResult
from meza.services import events as events_svc
from meza.services import risk_engine
from meza.tools.base import ToolContext


class ExecutiveAgent(Agent):
    agent_id = "executive"
    name = "MEZA Executive"
    description = "Daily Brief, company health, критические риски, кросс-департаментный анализ."
    capabilities = ["daily_brief", "needs_attention", "company_health"]
    allowed_tools = []
    risk_level = "LOW"

    async def handle(self, ctx: ToolContext, request: str, params: dict | None = None) -> AgentResult:
        risks = await risk_engine.list_open_risks(ctx.db, limit=100)
        changes = await events_svc.summarize_changes(ctx.db, hours=(params or {}).get("hours", 24))
        critical = [r for r in risks if r["severity"] == "CRITICAL"]
        high = [r for r in risks if r["severity"] == "HIGH"]
        summary = f"Открытых рисков: {len(risks)} (critical: {len(critical)}, high: {len(high)}). Событий за период: {changes['total']}."
        return AgentResult(
            status="success", summary=summary, risks=risks[:20],
            recommendations=[r["recommendation"] for r in (critical + high)[:5] if r.get("recommendation")],
            data={"risks": risks, "changes": changes, "critical_count": len(critical), "high_count": len(high)},
        )
