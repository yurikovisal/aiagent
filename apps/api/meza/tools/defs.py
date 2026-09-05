"""Concrete tool implementations backing the agents. Every tool talks to the
database (source of truth) — never to LLM memory — per §66.
"""

from __future__ import annotations

from datetime import date, timedelta

from sqlalchemy import func, select

from meza.core.rbac import Permission
from meza.core.utils import today, utcnow
from meza.models import (
    Customer,
    Deal,
    Document,
    Employee,
    Material,
    MaterialRequirement,
    Order,
    ProductionOrder,
    ProductionStage,
    PurchaseOrder,
    PurchaseRequest,
    Stock,
    Supplier,
    Task,
    WorkCenter,
)
from meza.rules.finance import compute_margin, explain_variance
from meza.rules.inventory import IncomingShipment, check_availability
from meza.rules.production import StageNode, propagate_delay
from meza.services import finance as finance_svc
from meza.services import production as production_svc
from meza.services import warehouse as warehouse_svc
from meza.tools.base import Tool, ToolContext, ToolResult, ToolRisk
from meza.tools.registry import register


def _source(table: str, record_id, extra: dict | None = None) -> dict:
    d = {"source": table, "record_id": record_id, "timestamp": utcnow().isoformat(), "confidence": 1.0}
    if extra:
        d.update(extra)
    return d


class GetOrderTool(Tool):
    name = "get_order"
    description = "Получить заказ по номеру или id, включая позиции и статус производства."
    risk = ToolRisk.READ
    required_permission = Permission.READ_SALES
    input_schema = {"type": "object", "properties": {"order_number": {"type": "string"}, "order_id": {"type": "integer"}}}

    async def run(self, ctx: ToolContext, order_number: str | None = None, order_id: int | None = None, **_) -> ToolResult:
        q = select(Order)
        if order_id:
            q = q.where(Order.id == order_id)
        elif order_number:
            q = q.where(Order.number == order_number)
        else:
            return ToolResult(ok=False, error="Укажите order_number или order_id.")
        order = (await ctx.db.execute(q)).scalar_one_or_none()
        if not order:
            return ToolResult(ok=False, error=f"Заказ {order_number or order_id} не найден.")
        po = (
            await ctx.db.execute(select(ProductionOrder).where(ProductionOrder.order_id == order.id))
        ).scalars().first()
        data = order.as_dict()
        if po:
            data["production_order"] = po.as_dict()
        return ToolResult(ok=True, data=data, summary=f"Заказ {order.number}: {order.status}", sources=[_source("orders", order.id)])


register(GetOrderTool())


class SearchOrdersTool(Tool):
    name = "search_orders"
    description = "Поиск заказов по статусу, приоритету, дедлайну или тексту."
    risk = ToolRisk.READ
    required_permission = Permission.READ_SALES
    input_schema = {
        "type": "object",
        "properties": {
            "status": {"type": "string"},
            "query": {"type": "string"},
            "deadline_within_days": {"type": "integer"},
            "limit": {"type": "integer"},
        },
    }

    async def run(self, ctx: ToolContext, status: str | None = None, query: str | None = None,
                  deadline_within_days: int | None = None, limit: int = 20, **_) -> ToolResult:
        q = select(Order)
        if status:
            q = q.where(Order.status == status)
        if query:
            q = q.where(Order.title.ilike(f"%{query}%") | Order.number.ilike(f"%{query}%"))
        if deadline_within_days is not None:
            q = q.where(Order.deadline.is_not(None), Order.deadline <= today() + timedelta(days=deadline_within_days))
        q = q.order_by(Order.deadline.asc().nullslast()).limit(limit)
        rows = (await ctx.db.execute(q)).scalars().all()
        data = [r.as_dict() for r in rows]
        return ToolResult(ok=True, data=data, summary=f"Найдено заказов: {len(data)}", sources=[_source("orders", "query")])


register(SearchOrdersTool())


class GetInventoryTool(Tool):
    name = "get_inventory"
    description = "Остатки материала на складе (в наличии, в резерве, доступно)."
    risk = ToolRisk.READ
    required_permission = Permission.READ_WAREHOUSE
    input_schema = {"type": "object", "properties": {"material_sku": {"type": "string"}, "material_name": {"type": "string"}}}

    async def run(self, ctx: ToolContext, material_sku: str | None = None, material_name: str | None = None, **_) -> ToolResult:
        material = await warehouse_svc.find_material(ctx.db, sku=material_sku, name=material_name)
        if not material:
            return ToolResult(ok=False, error=f"Материал '{material_sku or material_name}' не найден.")
        summary = await warehouse_svc.stock_summary(ctx.db, material.id)
        return ToolResult(
            ok=True,
            data=summary,
            summary=f"{material.name}: в наличии {summary['on_hand']:g}, резерв {summary['reserved']:g}, доступно {summary['available']:g} {material.unit}.",
            sources=[_source("inventory", material.id)],
        )


register(GetInventoryTool())


class CheckMaterialAvailabilityTool(Tool):
    name = "check_material_availability"
    description = "Проверить, хватит ли материала к нужной дате с учётом ожидаемых поставок; рассчитать дефицит."
    risk = ToolRisk.CALCULATE
    required_permission = Permission.READ_WAREHOUSE
    input_schema = {
        "type": "object",
        "properties": {
            "material_sku": {"type": "string"},
            "material_name": {"type": "string"},
            "required_quantity": {"type": "number"},
            "needed_by": {"type": "string", "format": "date"},
        },
        "required": ["required_quantity"],
    }

    async def run(self, ctx: ToolContext, required_quantity: float, material_sku: str | None = None,
                  material_name: str | None = None, needed_by: str | None = None, **_) -> ToolResult:
        material = await warehouse_svc.find_material(ctx.db, sku=material_sku, name=material_name)
        if not material:
            return ToolResult(ok=False, error=f"Материал '{material_sku or material_name}' не найден.")
        summary = await warehouse_svc.stock_summary(ctx.db, material.id)
        incoming_rows = await warehouse_svc.incoming_purchase_orders(ctx.db, material.id)
        incoming = [
            IncomingShipment(quantity=r.quantity, expected_at=r.expected_at, reference=r.number, supplier="")
            for r in incoming_rows
        ]
        needed_dt = date.fromisoformat(needed_by) if needed_by else None
        result = check_availability(
            material=material.name,
            required=required_quantity,
            on_hand=summary["on_hand"],
            reserved_by_others=summary["reserved"],
            needed_by=needed_dt,
            incoming=incoming,
        )
        return ToolResult(
            ok=True,
            data=result.as_dict(),
            summary=(
                f"{material.name}: требуется {required_quantity:g}, доступно {result.available:g}, "
                f"дефицит {result.shortage_after_incoming:g} {material.unit} ({result.status})."
            ),
            sources=[_source("inventory", material.id), _source("purchase_orders", "incoming")],
        )


register(CheckMaterialAvailabilityTool())


class GetProductionStatusTool(Tool):
    name = "get_production_status"
    description = "Статус производственного заказа: этапы, прогресс, блокировки, downstream-влияние задержки."
    risk = ToolRisk.READ
    required_permission = Permission.READ_PRODUCTION
    input_schema = {"type": "object", "properties": {"order_number": {"type": "string"}, "order_id": {"type": "integer"}}}

    async def run(self, ctx: ToolContext, order_number: str | None = None, order_id: int | None = None, **_) -> ToolResult:
        order = await production_svc.find_order(ctx.db, order_number=order_number, order_id=order_id)
        if not order:
            return ToolResult(ok=False, error=f"Заказ {order_number or order_id} не найден.")
        po = await production_svc.get_production_order(ctx.db, order.id)
        if not po:
            return ToolResult(ok=False, error=f"Для заказа {order.number} производственный заказ ещё не создан.")
        stages = await production_svc.get_stages(ctx.db, po.id)
        nodes = await production_svc.build_nodes(ctx.db, stages)
        impact = production_svc.compute_current_impact(stages, deadline=order.deadline, nodes=nodes)
        data = {
            "order": order.as_dict(),
            "production_order": po.as_dict(),
            "stages": [s.as_dict() for s in stages],
            "impact": impact.as_dict() if impact else None,
        }
        blocked = [s for s in stages if s.status == "BLOCKED"]
        summary = f"Заказ {order.number}: {po.status}, прогресс {po.progress * 100:.0f}%."
        if blocked:
            summary += f" Заблокировано этапов: {len(blocked)} ({', '.join(s.name for s in blocked)})."
        return ToolResult(ok=True, data=data, summary=summary, sources=[_source("production_orders", po.id)])


register(GetProductionStatusTool())


class CalculateOrderMarginTool(Tool):
    name = "calculate_order_margin"
    description = "Рассчитать план/факт себестоимости и маржинальность заказа по категориям затрат."
    risk = ToolRisk.CALCULATE
    required_permission = Permission.READ_FINANCE
    input_schema = {"type": "object", "properties": {"order_number": {"type": "string"}, "order_id": {"type": "integer"}}}

    async def run(self, ctx: ToolContext, order_number: str | None = None, order_id: int | None = None, **_) -> ToolResult:
        order = await production_svc.find_order(ctx.db, order_number=order_number, order_id=order_id)
        if not order:
            return ToolResult(ok=False, error=f"Заказ {order_number or order_id} не найден.")
        planned, actual = await finance_svc.cost_breakdown(ctx.db, order.id)
        result = compute_margin(order.revenue, planned, actual)
        explanation = explain_variance(result)
        data = result.as_dict()
        data["order_number"] = order.number
        data["explanation"] = explanation
        return ToolResult(
            ok=True,
            data=data,
            summary=f"Заказ {order.number}: маржа факт {  (result.actual_margin or 0) * 100:.1f}%. {explanation}",
            sources=[_source("costs", order.id), _source("orders", order.id, {"field": "revenue"})],
        )


register(CalculateOrderMarginTool())


class GetOverdueTasksTool(Tool):
    name = "get_overdue_tasks"
    description = "Список просроченных задач (across projects/production), опционально по подразделению."
    risk = ToolRisk.READ
    required_permission = Permission.READ_PROJECTS
    input_schema = {"type": "object", "properties": {"department_id": {"type": "integer"}, "limit": {"type": "integer"}}}

    async def run(self, ctx: ToolContext, department_id: int | None = None, limit: int = 50, **_) -> ToolResult:
        q = select(Task).where(Task.status.notin_(["DONE"]), Task.due_at.is_not(None), Task.due_at < utcnow())
        if department_id:
            q = q.where(Task.department_id == department_id)
        q = q.order_by(Task.due_at.asc()).limit(limit)
        rows = (await ctx.db.execute(q)).scalars().all()
        data = [r.as_dict() for r in rows]
        return ToolResult(ok=True, data=data, summary=f"Просроченных задач: {len(data)}.", sources=[_source("tasks", "overdue")])


register(GetOverdueTasksTool())


class SearchDocumentsTool(Tool):
    name = "search_documents"
    description = "Полнотекстовый / семантический поиск по документам (договоры, спецификации, регламенты)."
    risk = ToolRisk.READ
    required_permission = Permission.READ_DOCUMENTS
    input_schema = {"type": "object", "properties": {"query": {"type": "string"}, "doc_type": {"type": "string"}, "limit": {"type": "integer"}}}

    async def run(self, ctx: ToolContext, query: str, doc_type: str | None = None, limit: int = 10, **_) -> ToolResult:
        from meza.services.search import search_documents

        rows = await search_documents(ctx.db, query, doc_type=doc_type, limit=limit)
        return ToolResult(ok=True, data=rows, summary=f"Найдено документов: {len(rows)}.", sources=[_source("documents", "search")])


register(SearchDocumentsTool())


class CreatePurchaseRequestTool(Tool):
    name = "create_purchase_request"
    description = "Предложить заявку на закупку материала (требует утверждения человеком перед выполнением)."
    risk = ToolRisk.WRITE_LOW_RISK
    required_permission = Permission.WRITE_PROCUREMENT
    input_schema = {
        "type": "object",
        "properties": {
            "material_sku": {"type": "string"},
            "material_name": {"type": "string"},
            "quantity": {"type": "number"},
            "reason": {"type": "string"},
            "needed_by": {"type": "string", "format": "date"},
            "order_id": {"type": "integer"},
        },
        "required": ["quantity", "reason"],
    }

    async def run(self, ctx: ToolContext, quantity: float, reason: str, material_sku: str | None = None,
                  material_name: str | None = None, needed_by: str | None = None, order_id: int | None = None, **_) -> ToolResult:
        material = await warehouse_svc.find_material(ctx.db, sku=material_sku, name=material_name)
        if not material:
            return ToolResult(ok=False, error=f"Материал '{material_sku or material_name}' не найден.")
        from meza.services.approvals import propose_purchase_request

        approval = await propose_purchase_request(
            ctx.db,
            material=material,
            quantity=quantity,
            reason=reason,
            needed_by=date.fromisoformat(needed_by) if needed_by else None,
            order_id=order_id,
            agent_id=ctx.agent_id,
            user_id=ctx.user_id,
            run_id=ctx.run_id,
        )
        return ToolResult(
            ok=True,
            data={"approval_id": approval.id, "status": approval.status},
            summary=f"Предложена заявка на закупку: {material.name} {quantity:g} {material.unit}. Ожидает утверждения.",
            pending_approval_id=approval.id,
            sources=[_source("materials", material.id)],
        )


register(CreatePurchaseRequestTool())


class GetSupplierHistoryTool(Tool):
    name = "get_supplier_history"
    description = "История заказов поставщику: сроки поставки, цены, надёжность."
    risk = ToolRisk.READ
    required_permission = Permission.READ_PROCUREMENT
    input_schema = {"type": "object", "properties": {"supplier_id": {"type": "integer"}, "supplier_name": {"type": "string"}}}

    async def run(self, ctx: ToolContext, supplier_id: int | None = None, supplier_name: str | None = None, **_) -> ToolResult:
        q = select(Supplier)
        if supplier_id:
            q = q.where(Supplier.id == supplier_id)
        elif supplier_name:
            q = q.where(Supplier.name.ilike(f"%{supplier_name}%"))
        else:
            return ToolResult(ok=False, error="Укажите supplier_id или supplier_name.")
        supplier = (await ctx.db.execute(q)).scalars().first()
        if not supplier:
            return ToolResult(ok=False, error="Поставщик не найден.")
        pos = (await ctx.db.execute(select(PurchaseOrder).where(PurchaseOrder.supplier_id == supplier.id).order_by(PurchaseOrder.ordered_at.desc()).limit(20))).scalars().all()
        data = {"supplier": supplier.as_dict(), "purchase_orders": [p.as_dict() for p in pos]}
        return ToolResult(ok=True, data=data, summary=f"{supplier.name}: {len(pos)} заказов, on-time {supplier.on_time_rate * 100:.0f}%.", sources=[_source("suppliers", supplier.id)])


register(GetSupplierHistoryTool())


class GetDealsTool(Tool):
    name = "search_deals"
    description = "Сделки: по стадии, зависшие (нет активности N дней), по клиенту."
    risk = ToolRisk.READ
    required_permission = Permission.READ_SALES
    input_schema = {"type": "object", "properties": {"stage": {"type": "string"}, "stalled_days": {"type": "integer"}, "limit": {"type": "integer"}}}

    async def run(self, ctx: ToolContext, stage: str | None = None, stalled_days: int | None = None, limit: int = 30, **_) -> ToolResult:
        q = select(Deal).where(Deal.stage.notin_(["WON", "LOST"]))
        if stage:
            q = q.where(Deal.stage == stage)
        if stalled_days is not None:
            cutoff = utcnow() - timedelta(days=stalled_days)
            q = q.where((Deal.last_activity_at.is_(None)) | (Deal.last_activity_at < cutoff))
        q = q.limit(limit)
        rows = (await ctx.db.execute(q)).scalars().all()
        data = [r.as_dict() for r in rows]
        return ToolResult(ok=True, data=data, summary=f"Сделок найдено: {len(data)}.", sources=[_source("deals", "query")])


register(GetDealsTool())


class GetEventsTool(Tool):
    name = "get_recent_events"
    description = "Что изменилось за период — события из журнала (§36 What Changed)."
    risk = ToolRisk.READ
    required_permission = Permission.READ_OVERVIEW
    input_schema = {"type": "object", "properties": {"hours": {"type": "integer"}, "event_type": {"type": "string"}, "limit": {"type": "integer"}}}

    async def run(self, ctx: ToolContext, hours: int = 24, event_type: str | None = None, limit: int = 100, **_) -> ToolResult:
        from meza.services.events import recent_events

        rows = await recent_events(ctx.db, hours=hours, event_type=event_type, limit=limit)
        return ToolResult(ok=True, data=rows, summary=f"События за последние {hours} ч.: {len(rows)}.", sources=[_source("events", "query")])


register(GetEventsTool())


class GetRisksTool(Tool):
    name = "get_risks"
    description = "Текущие открытые риски (Risk Engine), опционально по домену/минимальной серьёзности."
    risk = ToolRisk.READ
    required_permission = Permission.READ_OVERVIEW
    input_schema = {"type": "object", "properties": {"domain": {"type": "string"}, "min_severity": {"type": "string"}, "limit": {"type": "integer"}}}

    async def run(self, ctx: ToolContext, domain: str | None = None, min_severity: str | None = None, limit: int = 50, **_) -> ToolResult:
        from meza.services.risk_engine import list_open_risks

        rows = await list_open_risks(ctx.db, domain=domain, min_severity=min_severity, limit=limit)
        return ToolResult(ok=True, data=rows, summary=f"Открытых рисков: {len(rows)}.", sources=[_source("risks", "query")])


register(GetRisksTool())


class GetEmployeeWorkloadTool(Tool):
    name = "get_department_workload"
    description = "Загрузка подразделения: открытые задачи, просрочки, сотрудники."
    risk = ToolRisk.READ
    required_permission = Permission.READ_EMPLOYEES
    input_schema = {"type": "object", "properties": {"department_id": {"type": "integer"}}}

    async def run(self, ctx: ToolContext, department_id: int, **_) -> ToolResult:
        emp_count = (await ctx.db.execute(select(func.count(Employee.id)).where(Employee.department_id == department_id))).scalar_one()
        open_tasks = (await ctx.db.execute(select(func.count(Task.id)).where(Task.department_id == department_id, Task.status != "DONE"))).scalar_one()
        overdue = (await ctx.db.execute(select(func.count(Task.id)).where(Task.department_id == department_id, Task.status != "DONE", Task.due_at < utcnow()))).scalar_one()
        data = {"department_id": department_id, "employees": emp_count, "open_tasks": open_tasks, "overdue_tasks": overdue}
        return ToolResult(ok=True, data=data, summary=f"Подразделение {department_id}: {emp_count} сотрудников, {open_tasks} задач, {overdue} просрочено.", sources=[_source("tasks", "aggregate")])


register(GetEmployeeWorkloadTool())


class SimulateDelayImpactTool(Tool):
    name = "simulate_delay_impact"
    description = "Смоделировать: что будет, если этап производства задержится ещё на N дней."
    risk = ToolRisk.CALCULATE
    required_permission = Permission.READ_PRODUCTION
    input_schema = {
        "type": "object",
        "properties": {"order_number": {"type": "string"}, "order_id": {"type": "integer"}, "extra_delay_days": {"type": "number"}},
        "required": ["extra_delay_days"],
    }

    async def run(self, ctx: ToolContext, extra_delay_days: float, order_number: str | None = None, order_id: int | None = None, **_) -> ToolResult:
        order = await production_svc.find_order(ctx.db, order_number=order_number, order_id=order_id)
        if not order:
            return ToolResult(ok=False, error=f"Заказ {order_number or order_id} не найден.")
        po = await production_svc.get_production_order(ctx.db, order.id)
        if not po:
            return ToolResult(ok=False, error="Производственный заказ не найден.")
        stages = await production_svc.get_stages(ctx.db, po.id)
        current = next((s for s in stages if s.status in ("IN_PROGRESS", "BLOCKED")), None) or (stages[0] if stages else None)
        if not current:
            return ToolResult(ok=False, error="Нет этапов производства для моделирования.")
        nodes = await production_svc.build_nodes(ctx.db, stages)
        result = propagate_delay(nodes, current.id, extra_delay_days, deadline=order.deadline)
        return ToolResult(
            ok=True,
            data=result.as_dict(),
            summary=f"Доп. задержка {extra_delay_days:g} дн. на этапе '{current.name}' → срыв дедлайна на {result.deadline_missed_by_days or 0:g} дн.",
            sources=[_source("production_stages", current.id)],
        )


register(SimulateDelayImpactTool())
