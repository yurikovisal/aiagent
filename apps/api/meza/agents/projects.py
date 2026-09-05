from __future__ import annotations

from meza.agents.base import Agent, AgentResult
from meza.orchestrator.executor import Budget, execute_tool
from meza.tools.base import ToolContext


class ProjectManagerAgent(Agent):
    agent_id = "projects"
    name = "Project Manager Agent"
    description = "Проекты, этапы, задачи, deadlines, dependencies, blockers."
    capabilities = ["overdue_tasks", "project_status"]
    allowed_tools = ["get_overdue_tasks"]
    risk_level = "LOW"

    async def handle(self, ctx: ToolContext, request: str, params: dict | None = None) -> AgentResult:
        params = params or {}
        budget = Budget(8, 10, 1)
        result = await execute_tool(ctx.db, tool_name="get_overdue_tasks", params={"department_id": params.get("department_id")}, ctx=ctx, budget=budget)
        if not result.ok:
            return AgentResult(status="error", summary=result.error or "Ошибка.", error=result.error)
        tasks = result.data or []
        findings = [{"type": "overdue_task", "task_id": t["id"], "title": t["title"], "due_at": t["due_at"]} for t in tasks]
        risks = [{"title": f"Просрочена задача «{t['title']}»", "severity": "MEDIUM", "entity_type": "task", "entity_id": t["id"]} for t in tasks[:10]]
        return AgentResult(status="success", summary=result.summary, findings=findings, risks=risks, sources=result.sources, data={"overdue_tasks": tasks})
