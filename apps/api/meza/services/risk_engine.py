"""Rule-based Risk Engine (§38). Deterministic rules over structured data; the LLM is used only
to explain/correlate afterwards, never to invent risks.

Thresholds are configuration, not code (§38 "правила хранить конфигурационно/в БД"): each rule
reads its parameters from the `risk_rules` table (falling back to the defaults below when no row
exists yet, and skipped entirely when a row exists with enabled=False). Manage them via
GET/PATCH /api/v1/risks/rules.
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
    Risk,
    RiskRule,
    Task,
)
from meza.rules.scoring import impact_from_amount, risk_score, severity_from_score, urgency_from_days
from meza.services import production as production_svc
from meza.services import warehouse as warehouse_svc

# rule_key -> (domain, default params, human description) — seeds risk_rules on first run and
# is the fallback whenever a row is missing (a fresh DB, or a rule added after deployment).
RULE_DEFAULTS: dict[str, dict] = {
    "deadline_at_risk": {"deadline_hours": 48, "progress_threshold": 0.7},
    "material_below_min": {},
    "receivable_overdue": {"threshold_days": 5},
    "production_stage_blocked": {},
    "material_eta_late": {},
    "task_overdue": {"medium_days": 5},
    "cost_overrun": {"threshold_pct": 10.0},
}

RULE_DOMAINS: dict[str, str] = {
    "deadline_at_risk": "production", "material_below_min": "warehouse", "receivable_overdue": "finance",
    "production_stage_blocked": "production", "material_eta_late": "procurement", "task_overdue": "projects",
    "cost_overrun": "finance",
}

RULE_LABELS: dict[str, str] = {
    "deadline_at_risk": "Дедлайн заказа под угрозой (deadline < N часов И прогресс < X%)",
    "material_below_min": "Материал ниже минимального остатка",
    "receivable_overdue": "Просроченная дебиторская задолженность",
    "production_stage_blocked": "Этап производства заблокирован",
    "material_eta_late": "Поставка материала опаздывает к старту производства",
    "task_overdue": "Просроченная задача",
    "cost_overrun": "Перерасход бюджета по заказу",
}


async def get_rule_config(db: AsyncSession) -> dict[str, dict]:
    """Returns rule_key -> {"enabled": bool, "params": dict}, DB rows merged over defaults."""
    rows = (await db.execute(select(RiskRule))).scalars().all()
    by_key = {r.rule_key: r for r in rows}
    out = {}
    for rule_key, defaults in RULE_DEFAULTS.items():
        row = by_key.get(rule_key)
        if row:
            out[rule_key] = {"enabled": row.enabled, "params": {**defaults, **(row.params or {})}}
        else:
            out[rule_key] = {"enabled": True, "params": dict(defaults)}
    return out


async def ensure_default_rules(db: AsyncSession) -> None:
    """Idempotently create risk_rules rows for any rule that doesn't have one yet, so the
    thresholds are visible/editable in the DB from the start rather than only living in code."""
    existing_keys = {r.rule_key for r in (await db.execute(select(RiskRule))).scalars().all()}
    for rule_key, defaults in RULE_DEFAULTS.items():
        if rule_key in existing_keys:
            continue
        db.add(RiskRule(
            rule_key=rule_key, name=RULE_LABELS.get(rule_key, rule_key), domain=RULE_DOMAINS.get(rule_key, "general"),
            enabled=True, params=dict(defaults), default_severity="MEDIUM",
        ))
    await db.flush()


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


async def rule_deadline_at_risk(db: AsyncSession, params: dict) -> list[Risk]:
    """deadline < N hours AND progress < X% (both configurable via risk_rules)."""
    out = []
    deadline_days = params["deadline_hours"] / 24
    cutoff = today() + timedelta(hours=params["deadline_hours"])
    progress_threshold = params["progress_threshold"]
    q = select(Order).where(Order.deadline.is_not(None), Order.deadline <= cutoff, Order.progress < progress_threshold,
                             Order.status.notin_(["DELIVERED", "INSTALLED", "CLOSED", "CANCELLED"]))
    for order in (await db.execute(q)).scalars().all():
        days_left = (order.deadline - today()).days
        score = risk_score("HIGH", impact_from_amount(order.revenue), urgency_from_days(days_left, deadline_days))
        out.append(await _upsert_risk(
            db,
            rule_key="deadline_at_risk", domain="production",
            entity_type="order", entity_id=order.id, entity_label=order.number,
            title=f"Заказ {order.number}: риск срыва дедлайна",
            cause=f"До дедлайна {days_left} дн., прогресс {order.progress * 100:.0f}% (порог {progress_threshold * 100:.0f}%).",
            impact="Возможна задержка поставки клиенту.",
            recommendation="Проверить статус производства и ускорить критический этап.",
            severity=severity_from_score(score), impact_score=impact_from_amount(order.revenue),
            urgency_score=urgency_from_days(days_left, deadline_days), confidence=1.0, score=score,
            evidence=[{"fact": f"deadline={order.deadline.isoformat()}", "source": "orders", "record_id": order.id}],
            actions=[], related_order_id=order.id,
        ))
    return out


async def rule_stock_below_reserved(db: AsyncSession, params: dict) -> list[Risk]:
    """material available < material.min_stock (the threshold itself is per-material, set on
    the Material row by warehouse staff — this rule has no engine-level knob of its own)."""
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


async def rule_receivable_overdue(db: AsyncSession, params: dict) -> list[Risk]:
    out = []
    threshold_days = params["threshold_days"]
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
            cause=f"Платёж просрочен на {days_overdue} дн. (порог {threshold_days} дн.), сумма {p.amount:,.0f} {p.currency}.",
            impact="Риск кассового разрыва.",
            recommendation="Связаться с клиентом, запросить оплату.",
            severity=severity_from_score(score), impact_score=impact_from_amount(p.amount), urgency_score=1.0,
            confidence=1.0, score=score,
            evidence=[{"fact": f"due_date={p.due_date.isoformat()}", "source": "payments", "record_id": p.id}],
            actions=[], related_order_id=p.order_id,
        ))
    return out


async def rule_production_blocked(db: AsyncSession, params: dict) -> list[Risk]:
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
            evidence=[{"fact": "status=BLOCKED", "source": "production_stages", "record_id": stage.id}],
            actions=[], related_order_id=order.id if order else None,
        ))
    return out


async def rule_material_eta_late(db: AsyncSession, params: dict) -> list[Risk]:
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
                    title="Поставка материала опаздывает к старту производства" + (f" (заказ {order.number})" if order else ""),
                    cause=f"Материал ожидается {late[0].expected_at.isoformat()}, производство должно начаться {po.planned_start.isoformat()} (+{days_late} дн.).",
                    impact="Задержка старта производства.",
                    recommendation="Ускорить поставку или пересмотреть план производства.",
                    severity=severity_from_score(score), impact_score=impact_from_amount(order.revenue if order else 0),
                    urgency_score=urgency_from_days(0, 5), confidence=1.0, score=score,
                    evidence=[{"fact": f"eta={late[0].expected_at.isoformat()}", "source": "purchase_orders", "record_id": late[0].id}],
                    actions=[], related_order_id=po.order_id,
                ))
    return out


async def rule_task_overdue(db: AsyncSession, params: dict) -> list[Risk]:
    out = []
    medium_days = params["medium_days"]
    q = select(Task).where(Task.status.notin_(["DONE"]), Task.due_at.is_not(None), Task.due_at < utcnow())
    for t in (await db.execute(q)).scalars().all():
        days = (utcnow() - t.due_at).days
        score = risk_score("MEDIUM" if days < medium_days else "HIGH", 0.3, urgency_from_days(-days, 10))
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


async def rule_cost_overrun(db: AsyncSession, params: dict) -> list[Risk]:
    from meza.rules.finance import compute_margin
    from meza.services.finance import cost_breakdown

    out = []
    threshold_pct = params["threshold_pct"]
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
                cause=f"Факт превышает план на {result.cost_variance_pct:.1f}% ({result.cost_variance:,.0f}), порог {threshold_pct:g}%.",
                impact="Снижение маржинальности заказа.",
                recommendation="Проверить категории затрат с наибольшим отклонением.",
                severity=severity_from_score(score), impact_score=impact_from_amount(abs(result.cost_variance)),
                urgency_score=0.4, confidence=1.0, score=score,
                evidence=[{"fact": f"variance_pct={result.cost_variance_pct}", "source": "costs", "record_id": order.id}],
                actions=[], related_order_id=order.id,
            ))
    return out


ALL_RULES = {
    "deadline_at_risk": rule_deadline_at_risk,
    "material_below_min": rule_stock_below_reserved,
    "receivable_overdue": rule_receivable_overdue,
    "production_stage_blocked": rule_production_blocked,
    "material_eta_late": rule_material_eta_late,
    "task_overdue": rule_task_overdue,
    "cost_overrun": rule_cost_overrun,
}


async def run_all_rules(db: AsyncSession) -> list[Risk]:
    await ensure_default_rules(db)
    config = await get_rule_config(db)
    all_risks: list[Risk] = []
    for rule_key, rule_fn in ALL_RULES.items():
        cfg = config.get(rule_key, {"enabled": True, "params": RULE_DEFAULTS.get(rule_key, {})})
        if not cfg["enabled"]:
            continue
        all_risks.extend(await rule_fn(db, cfg["params"]))
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
