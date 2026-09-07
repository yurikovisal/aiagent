from __future__ import annotations

from meza.agents.base import Agent, AgentResult
from meza.orchestrator.executor import Budget, execute_tool
from meza.tools.base import ToolContext


class HRAgent(Agent):
    """Uses only legitimately, transparently accessible corporate data (§22). No covert surveillance."""

    agent_id = "hr"
    name = "HR / KPI Agent"
    description = (
        "Загрузка подразделений, KPI, посещаемость — только прозрачные корпоративные данные. "
        "Чтобы узнать нагрузку подразделения по названию, сначала найди его id через "
        "list_departments, затем вызови get_department_workload."
    )
    capabilities = ["department_workload"]
    allowed_tools = ["get_department_workload", "list_departments"]
    risk_level = "LOW"

    async def handle(self, ctx: ToolContext, request: str, params: dict | None = None, budget: Budget | None = None) -> AgentResult:
        params = params or {}
        budget = budget or Budget(8, 10, 1)

        if params.get("department_id"):
            result = await execute_tool(ctx.db, tool_name="get_department_workload", params={"department_id": params["department_id"]}, ctx=ctx, budget=budget)
            if not result.ok:
                return AgentResult(status="error", summary=result.error or "Ошибка.", error=result.error)
            return AgentResult(status="success", summary=result.summary, sources=result.sources, data=result.data)

        # "Какое подразделение перегружено?" / "нагрузка производства" — no numeric id available,
        # only a name. Let the LLM resolve the name via list_departments, then check workload.
        reasoned = await self.reason(ctx, request, budget, params_hint=params or None)
        if reasoned is not None:
            return reasoned
        return AgentResult(status="insufficient_data", summary="Недостаточно данных: не указано подразделение.")
