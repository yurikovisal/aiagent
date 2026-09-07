from __future__ import annotations

from meza.agents.base import Agent, AgentResult
from meza.orchestrator.executor import Budget, execute_tool
from meza.tools.base import ToolContext


class DocumentAgent(Agent):
    agent_id = "documents"
    name = "Document Agent"
    description = (
        "Поиск, классификация и Q&A по документам (договоры, спецификации, регламенты). "
        "Извлекай из запроса ключевые слова для поиска и, если запрос называет тип документа "
        "(договор, счёт, спецификация, регламент, инструкция, техдокумент, отчёт), передавай его "
        "как doc_type (CONTRACT, INVOICE, SPECIFICATION, REGULATION, INSTRUCTION, TECH_DOC, REPORT)."
    )
    capabilities = ["search", "qa"]
    allowed_tools = ["search_documents", "get_business_memory"]
    risk_level = "LOW"

    async def handle(self, ctx: ToolContext, request: str, params: dict | None = None, budget: Budget | None = None) -> AgentResult:
        params = params or {}
        budget = budget or Budget(8, 10, 1)

        reasoned = await self.reason(ctx, request, budget, params_hint=params or None)
        if reasoned is not None:
            return reasoned

        query = params.get("query") or request
        result = await execute_tool(ctx.db, tool_name="search_documents", params={"query": query, "doc_type": params.get("doc_type")}, ctx=ctx, budget=budget)
        if not result.ok:
            return AgentResult(status="error", summary=result.error or "Ошибка поиска.", error=result.error)
        return AgentResult(status="success", summary=result.summary, sources=result.sources, data={"documents": result.data})
