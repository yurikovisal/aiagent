from __future__ import annotations

from meza.agents.base import Agent, AgentResult
from meza.orchestrator.executor import Budget, execute_tool
from meza.tools.base import ToolContext


class DocumentAgent(Agent):
    agent_id = "documents"
    name = "Document Agent"
    description = "Поиск, классификация и Q&A по документам (договоры, спецификации, регламенты)."
    capabilities = ["search", "qa"]
    allowed_tools = ["search_documents"]
    risk_level = "LOW"

    async def handle(self, ctx: ToolContext, request: str, params: dict | None = None) -> AgentResult:
        params = params or {}
        query = params.get("query") or request
        budget = Budget(8, 10, 1)
        result = await execute_tool(ctx.db, tool_name="search_documents", params={"query": query, "doc_type": params.get("doc_type")}, ctx=ctx, budget=budget)
        if not result.ok:
            return AgentResult(status="error", summary=result.error or "Ошибка поиска.", error=result.error)
        return AgentResult(status="success", summary=result.summary, sources=result.sources, data={"documents": result.data})
