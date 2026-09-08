from __future__ import annotations

from meza.agents.base import Agent, AgentResult
from meza.orchestrator.executor import Budget, execute_tool
from meza.tools.base import ToolContext


class ProjectManagerAgent(Agent):
    agent_id = "projects"
    name = "Project Manager Agent"
    description = (
        "Проекты, этапы, задачи, deadlines, dependencies, blockers. Чтобы объяснить, почему "
        "задерживается конкретный проект, сначала найди его через search_projects, затем вызови "
        "get_project_delay_analysis — он строит причинно-следственную цепочку до корневой задачи."
    )
    capabilities = ["overdue_tasks", "project_status", "delay_root_cause"]
    allowed_tools = ["get_overdue_tasks", "search_projects", "get_project_delay_analysis"]
    risk_level = "LOW"

    async def handle(self, ctx: ToolContext, request: str, params: dict | None = None, budget: Budget | None = None) -> AgentResult:
        params = params or {}
        budget = budget or Budget(8, 10, 1)

        if _looks_targeted(request):
            reasoned = await self.reason(ctx, request, budget, params_hint=params or None)
            if reasoned is not None:
                return reasoned

        result = await execute_tool(ctx.db, tool_name="get_overdue_tasks", params={"department_id": params.get("department_id")}, ctx=ctx, budget=budget)
        if not result.ok:
            return AgentResult(status="error", summary=result.error or "Ошибка.", error=result.error)
        tasks = result.data or []
        findings = [{"type": "overdue_task", "task_id": t["id"], "title": t["title"], "due_at": t["due_at"]} for t in tasks]
        risks = [{"title": f"Просрочена задача «{t['title']}»", "severity": "MEDIUM", "entity_type": "task", "entity_id": t["id"]} for t in tasks[:10]]
        return AgentResult(status="success", summary=result.summary, findings=findings, risks=risks, sources=result.sources, data={"overdue_tasks": tasks})


def _looks_targeted(request: str) -> bool:
    lowered = request.lower()
    return any(w in lowered for w in ("задерж", "почему", "проект", "срыв"))
