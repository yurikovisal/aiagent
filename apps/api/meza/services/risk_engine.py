"""Rule-based Risk Engine (§38). Deterministic rules over structured data; the LLM is used only
to explain/correlate afterwards, never to invent risks.
"""

from __future__ import annotations

import hashlib
from datetime import timedelta

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from meza.core.utils import today, utcnow
from meza.models import (
    Order,
    Payment,
    ProductionOrder,
    ProductionStage,
    PurchaseOrder,
    Task,
)
from meza.rules.scoring import impact_from_amount, risk_score, severity_from_score, urgency_from_days
from meza.services import production as production_svc
from meza.services import warehouse as warehouse_svc
from meza.models import Risk


def _fingerprint(rule_key: str, entity_type: str, entity_id) -> str:
    return hashlib.sha1(f"{rule_key}:{entity_type}:{entity_id}".encode()).hexdigest()[:32]


async def _upsert_risk(db: AsyncSession, **kwargs) -> Risk:
    if "entity_id" in kwargs:
        kwargs["entity_id"] = str(kwargs["entity_id"])
    fp = _fingerprint(kwargs["rule_key"], kwargs["entity_type"], kwargs["entity_id"])
    existing = (await db.execute(select(Risk).where(Risk.fingerprint == fp))).scalars().first()
    now = utcnow()
    if existing:
        for k, v in kwargs.items():
            setattr(existing, k, v)
        existing.last_detected_at = now
        if existing.status == "RESOLVED":
            existing.status = "OPEN"
        await db.flush()
        return existing
    risk = Risk(fingerprint=fp, first_detected_at=now, last_detected_at=now, status="OPEN", **kwargs)
    db.add(risk)
    await db.flush()
    return risk


async def rule_deadline_at_risk(db: AsyncSession) -> list[Risk]:
    """deadline < 48h AND progress < 70%"""
    out = []
    cutoff = today() + timedelta(days=2)
    q = select(Order).where(Order.deadline.is_not(None), Order.deadline <= cutoff, Order.progress < 0.7,
                             Order.status.notin_(["DELIVERED", "INSTALLED", "CLOSED", "CANCELLED"]))
    for order in (await db.execute(q)).scalars().all():
        days_left = (order.deadline - today()).days
        score = risk_score("HIGH", impact_from_amount(order.revenue), urgency_from_days(days_left, 2))
        out.append(await _upsert_risk(
            db,
            rule_key="deadline_at_risk", domain="production",
            entity_type="order", entity_id=order.id, entity_label=order.number,
            title=f"Заказ {order.number}: риск срыва дедлайна",
            cause=f"До дедлайна {days_left} дн., прогресс {order.progress * 100:.0f}%.",
            impact="Возможна задержка поставки клиенту.",
            recommendation="Проверить статус производства и ускорить критический этап.",
            severity=severity_from_score(score), impact_score=impact_from_amount(order.revenue),
            urgency_score=urgency_from_days(days_left, 2), confidence=1.0, score=score,
            evidence=[{"fact": f"deadline={order.deadline.isoformat()}", "source": "orders", "record_id": order.id}],
            actions=[], related_order_id=order.id,
        ))
    return out


async def rule_stock_below_reserved(db: AsyncSession) -> list[Risk]:
    """stock < reserved -> already oversold material."""
    out = []
    low = await warehouse_svc.low_stock_materials(db)
    for m in low:
        score = risk_score("MEDIUM", impact_from_amount(m["shortage_below_min"] * 1000, reference=5_000_000), 0.5)
        out.append(await _upsert_risk(
            db,
            rule_key="material_below_min", domain="warehouse",
            entity_type="material", entity_id=m["material_id"], entity_label=m["material_name"],
            title=f"Материал '{m['material_name']}' ниже минимального остатка",
            cause=f"Доступно {m['available']:g} {m['unit']}, минимум {m['min_stock']:g}.",
            impact="Риск дефицита для новых производственных заказов.",
            recommendation="Создать заявку на закупку.",
            severity=severity_from_score(score), impact_score=0.5, urgency_score=0.5, confidence=1.0, score=score,
            evidence=[{"fact": f"available={m['available']}", "source": "inventory", "record_id": m["material_id"]}],
            actions=[{"tool": "create_purchase_request", "params": {"material_sku": m.get("sku"), "quantity": m["shortage_below_min"]}}],
            related_order_id=None,
        ))
    return out


async def rule_receivable_overdue(db: AsyncSession, threshold_days: int = 5) -> list[Risk]:
    out = []
    cutoff = today() - timedelta(days=threshold_days)
    q = select(Payment).where(Payment.direction == "IN", Payment.status != "PAID", Payment.due_date.is_not(None), Payment.due_date < cutoff)
    for p in (await db.execute(q)).scalars().all():
        days_overdue = (today() - p.due_date).days
        score = risk_score("HIGH", impact_from_amount(p.amount), 1.0)
        out.append(await _upsert_risk(
            db,
            rule_key="receivable_overdue", domain="finance",
            entity_type="payment", entity_id=p.id, entity_label=p.counterparty,
            title=f"Просроченная дебиторская задолженность: {p.counterparty}",
            cause=f"Платёж просрочен на {days_overdue} дн., сумма {p.amount:,.0f} {p.currency}.",
            impact="Риск кассового разрыва.",
            recommendation="Связаться с клиентом, запросить оплату.",
            severity=severity_from_score(score), impact_score=impact_from_amount(p.amount), urgency_score=1.0,
            confidence=1.0, score=score,
            evidence=[{"fact": f"due_date={p.due_date.isoformat()}", "source": "payments", "record_id": p.id}],
            actions=[], related_order_id=p.order_id,
        ))
    return out


async def rule_production_blocked(db: AsyncSession) -> list[Risk]:
    out = []
    q = select(ProductionStage).where(ProductionStage.status == "BLOCKED")
    for stage in (await db.execute(q)).scalars().all():
        po = await db.get(ProductionOrder, stage.production_order_id)
        order = await db.get(Order, po.order_id) if po else None
        score = risk_score("HIGH", impact_from_amount(order.revenue if order else 0), 0.8)
        out.append(await _upsert_risk(
            db,
            rule_key="production_stage_blocked", domain="production",
            entity_type="production_stage", entity_id=stage.id, entity_label=stage.name,
            title=f"Этап производства заблокирован: {stage.name}" + (f" (заказ {order.number})" if order else ""),
            cause=stage.blocked_reason or "Причина не указана.",
            impact="Блокирует последующие этапы производства.",
            recommendation="Устранить причину блокировки или перепланировать участок.",
            severity=severity_from_score(score), impact_score=impact_from_amount(order.revenue if order else 0),
            urgency_score=0.8, confidence=1.0, score=score,
            evidence=[{"fact": f"status=BLOCKED", "source": "production_stages", "record_id": stage.id}],
            actions=[], related_order_id=order.id if order else None,
        ))
    return out


async def rule_material_eta_late(db: AsyncSession) -> list[Risk]:
    """material ETA > production start"""
    out = []
    q = select(ProductionOrder).where(ProductionOrder.status.in_(["PLANNED", "IN_PROGRESS"]))
    for po in (await db.execute(q)).scalars().all():
        if not po.planned_start:
            continue
        from meza.models import MaterialRequirement

        reqs = (await db.execute(select(MaterialRequirement).where(MaterialRequirement.production_order_id == po.id))).scalars().all()
        for req in reqs:
            incoming = await warehouse_svc.incoming_purchase_orders(db, req.material_id)
            late = [i for i in incoming if i.expected_at and i.expected_at > po.planned_start]
            if late and req.consumed_quantity < req.quantity:
                order = await db.get(Order, po.order_id)
                days_late = (late[0].expected_at - po.planned_start).days
                score = risk_score("HIGH", impact_from_amount(order.revenue if order else 0), urgency_from_days(0, 5))
                out.append(await _upsert_risk(
                    db,
                    rule_key="material_eta_late", domain="procurement",
                    entity_type="material_requirement", entity_id=req.id,
                    entity_label=order.number if order else str(po.id),
                    title=f"Поставка материала опаздывает к старту производства" + (f" (заказ {order.number})" if order else ""),
                    cause=f"Материал ожидается {late[0].expected_at.isoformat()}, производство должно начаться {po.planned_start.isoformat()} (+{days_late} дн.).",
                    impact="Задержка старта производства.",
                    recommendation="Ускорить поставку или пересмотреть план производства.",
                    severity=severity_from_score(score), impact_score=impact_from_amount(order.revenue if order else 0),
                    urgency_score=urgency_from_days(0, 5), confidence=1.0, score=score,
                    evidence=[{"fact": f"eta={late[0].expected_at.isoformat()}", "source": "purchase_orders", "record_id": late[0].id}],
                    actions=[], related_order_id=po.order_id,
                ))
    return out


async def rule_task_overdue(db: AsyncSession) -> list[Risk]:
    out = []
    q = select(Task).where(Task.status.notin_(["DONE"]), Task.due_at.is_not(None), Task.due_at < utcnow())
    for t in (await db.execute(q)).scalars().all():
        days = (utcnow() - t.due_at).days
        score = risk_score("MEDIUM" if days < 5 else "HIGH", 0.3, urgency_from_days(-days, 10))
        out.append(await _upsert_risk(
            db,
            rule_key="task_overdue", domain="projects",
            entity_type="task", entity_id=t.id, entity_label=t.title,
            title=f"Просрочена задача: {t.title}",
            cause=f"Просрочена на {days} дн.",
            impact="Может задержать проект/заказ.",
            recommendation="Назначить/эскалировать исполнителю.",
            severity=severity_from_score(score), impact_score=0.3, urgency_score=urgency_from_days(-days, 10),
            confidence=1.0, score=score,
            evidence=[{"fact": f"due_at={t.due_at.isoformat()}", "source": "tasks", "record_id": t.id}],
            actions=[], related_order_id=t.order_id,
        ))
    return out


async def rule_cost_overrun(db: AsyncSession, threshold_pct: float = 10.0) -> list[Risk]:
    from meza.rules.finance import compute_margin
    from meza.services.finance import cost_breakdown

    out = []
    q = select(Order).where(Order.status.notin_(["CANCELLED"]))
    for order in (await db.execute(q)).scalars().all():
        planned, actual = await cost_breakdown(db, order.id)
        if not planned and not actual:
            continue
        result = compute_margin(order.revenue, planned, actual)
        if result.cost_variance_pct and result.cost_variance_pct > threshold_pct:
            score = risk_score("MEDIUM", impact_from_amount(abs(result.cost_variance)), 0.4)
            out.append(await _upsert_risk(
                db,
                rule_key="cost_overrun", domain="finance",
                entity_type="order", entity_id=order.id, entity_label=order.number,
                title=f"Перерасход бюджета по заказу {order.number}",
                cause=f"Факт превышает план на {result.cost_variance_pct:.1f}% ({result.cost_variance:,.0f}).",
                impact="Снижение маржинальности заказа.",
                recommendation="Проверить категории затрат с наибольшим отклонением.",
                severity=severity_from_score(score), impact_score=impact_from_amount(abs(result.cost_variance)),
                urgency_score=0.4, confidence=1.0, score=score,
                evidence=[{"fact": f"variance_pct={result.cost_variance_pct}", "source": "costs", "record_id": order.id}],
                actions=[], related_order_id=order.id,
            ))
    return out


ALL_RULES = [
    rule_deadline_at_risk,
    rule_stock_below_reserved,
    rule_receivable_overdue,
    rule_production_blocked,
    rule_material_eta_late,
    rule_task_overdue,
    rule_cost_overrun,
]


async def run_all_rules(db: AsyncSession) -> list[Risk]:
    all_risks: list[Risk] = []
    for rule in ALL_RULES:
        all_risks.extend(await rule(db))
    await db.flush()
    return all_risks


async def list_open_risks(db: AsyncSession, *, domain: str | None = None, min_severity: str | None = None, limit: int = 50) -> list[dict]:
    q = select(Risk).where(Risk.status == "OPEN")
    if domain:
        q = q.where(Risk.domain == domain)
    q = q.order_by(Risk.score.desc()).limit(limit)
    rows = (await db.execute(q)).scalars().all()
    out = [r.as_dict() for r in rows]
    if min_severity:
        order = ["LOW", "MEDIUM", "HIGH", "CRITICAL"]
        idx = order.index(min_severity) if min_severity in order else 0
        out = [r for r in out if order.index(r["severity"]) >= idx]
    return out
