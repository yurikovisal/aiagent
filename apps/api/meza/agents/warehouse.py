from __future__ import annotations

from meza.agents.base import Agent, AgentResult
from meza.orchestrator.executor import Budget, execute_tool
from meza.services import warehouse as warehouse_svc
from meza.tools.base import ToolContext


class WarehouseAgent(Agent):
    agent_id = "warehouse"
    name = "Warehouse Agent"
    description = "Остатки, движения, резерв, дефицит, медленно оборачиваемые материалы."
    capabilities = ["stock", "availability", "low_stock", "slow_moving"]
    allowed_tools = ["get_inventory", "check_material_availability"]
    risk_level = "LOW"

    async def handle(self, ctx: ToolContext, request: str, params: dict | None = None, budget: Budget | None = None) -> AgentResult:
        params = params or {}
        budget = budget or Budget(8, 10, 1)
        material_name = params.get("material_name") or params.get("material_sku")

        if material_name:
            # Exact material already known (e.g. from an earlier extraction) — go straight to the tool.
            result = await execute_tool(
                ctx.db, tool_name="get_inventory",
                params={"material_sku": params.get("material_sku"), "material_name": params.get("material_name")},
                ctx=ctx, budget=budget,
            )
            if not result.ok:
                return AgentResult(status="insufficient_data", summary=result.error or "Материал не найден.", error=result.error)
            return AgentResult(status="success", summary=result.summary, sources=result.sources, data=result.data)

        # Free-text request (e.g. "хватит ли трубы 40x40x2 на 1800 кг к 8 сентября?") — let the
        # LLM extract the material name / quantity / date and pick get_inventory vs
        # check_material_availability, rather than only ever running the broad low-stock scan.
        if _looks_specific(request):
            reasoned = await self.reason(ctx, request, budget, params_hint=params or None)
            if reasoned is not None:
                return reasoned

        low = await warehouse_svc.low_stock_materials(ctx.db)
        slow = await warehouse_svc.slow_moving_materials(ctx.db)
        findings = [{"type": "low_stock", **m} for m in low] + [{"type": "slow_moving", **m} for m in slow]
        risks = [
            {"title": f"Материал «{m['material_name']}» ниже минимума", "severity": "MEDIUM", "entity_type": "material", "entity_id": m["material_id"]}
            for m in low
        ]
        summary = f"Ниже минимума: {len(low)} материалов. Без движения: {len(slow)}."
        return AgentResult(
            status="success", summary=summary, findings=findings, risks=risks,
            recommendations=["Создать заявки на закупку для позиций ниже минимума."] if low else [],
            data={"low_stock": low, "slow_moving": slow},
        )


def _looks_specific(request: str) -> bool:
    """Heuristic: does this request plausibly name a material / quantity, as opposed to a broad
    'show me the warehouse' question? Avoids spending an LLM round-trip on generic requests."""
    lowered = request.lower()
    has_digit = any(ch.isdigit() for ch in request)
    specific_words = ("хватит", "хватает", "наличи", "остат", "нужно", "требуется", "запас")
    return has_digit or any(w in lowered for w in specific_words)
