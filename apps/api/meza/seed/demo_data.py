"""Synthetic ATON+ dataset for development (§51). Every row is flagged is_demo=True and must
never be mixed with real production data — `make seed` refuses to run against a database that
already has non-demo business rows.
"""

from __future__ import annotations

from datetime import date, timedelta

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from meza.core.security import hash_password
from meza.core.utils import today, utcnow
from meza.models import (
    Attendance,
    Campaign,
    Cost,
    Customer,
    Deal,
    Department,
    Document,
    Employee,
    Event,
    Expense,
    KPI,
    Lead,
    Material,
    MaterialRequirement,
    Order,
    OrderItem,
    Payment,
    Project,
    ProductionOrder,
    ProductionStage,
    PurchaseOrder,
    RoleRecord,
    StageDependency,
    Stock,
    Supplier,
    SupplierOffer,
    Task,
    Tender,
    User,
    Warehouse,
    WorkCenter,
    Workflow,
)
from meza.core.rbac import Role, permissions_for


async def _get_or_create_admin(db: AsyncSession, email: str, password: str) -> User:
    existing = (await db.execute(select(User).where(User.email == email))).scalars().first()
    if existing:
        return existing
    user = User(email=email, full_name="ATON+ Admin", password_hash=hash_password(password), role=Role.ADMIN.value, is_active=True)
    db.add(user)
    await db.flush()
    return user


async def seed_roles(db: AsyncSession) -> None:
    for role in Role:
        existing = (await db.execute(select(RoleRecord).where(RoleRecord.name == role.value))).scalars().first()
        if not existing:
            db.add(RoleRecord(name=role.value, permissions=sorted(p.value for p in permissions_for(role))))
    await db.flush()


async def seed_demo(db: AsyncSession) -> dict:
    """Idempotent-ish demo seed: safe to re-run on an empty demo DB."""
    await seed_roles(db)

    dep_prod = Department(code="PRODUCTION", name="Производство", is_demo=True)
    dep_sales = Department(code="SALES", name="Продажи", is_demo=True)
    dep_wh = Department(code="WAREHOUSE", name="Склад", is_demo=True)
    db.add_all([dep_prod, dep_sales, dep_wh])
    await db.flush()

    emp1 = Employee(full_name="Азамат Нурланов", role_title="Начальник производства", department_id=dep_prod.id, is_demo=True)
    emp2 = Employee(full_name="Гульнара Ахметова", role_title="Менеджер по продажам", department_id=dep_sales.id, is_demo=True)
    emp3 = Employee(full_name="Данияр Серіков", role_title="Кладовщик", department_id=dep_wh.id, is_demo=True)
    db.add_all([emp1, emp2, emp3])
    await db.flush()

    for emp in (emp1, emp2, emp3):
        db.add(Attendance(employee_id=emp.id, day=today(), status="PRESENT", hours=8, is_demo=True))
    db.add(KPI(department_id=dep_prod.id, name="Своевременность заказов", period=today().strftime("%Y-%m"), target=95, actual=87, unit="%", is_demo=True))

    customer = Customer(name="ТОО СтройИнвест", segment="Строительство", contact_name="Ержан Т.",
                         contact_email="info@stroyinvest.example", is_demo=True)
    db.add(customer)
    await db.flush()

    deal = Deal(code="DL-2001", title="Металлоконструкции для склада", customer_id=customer.id, owner_employee_id=emp2.id,
                stage="NEGOTIATION", amount=18_500_000, probability=0.6,
                expected_close=today() + timedelta(days=10), last_activity_at=utcnow() - timedelta(days=20),
                is_demo=True)
    deal_stalled = Deal(code="DL-2002", title="Навес для автостоянки", customer_id=customer.id, owner_employee_id=emp2.id,
                         stage="PROPOSAL", amount=4_200_000, probability=0.3,
                         last_activity_at=utcnow() - timedelta(days=25), is_demo=True)
    db.add_all([deal, deal_stalled])
    await db.flush()

    project = Project(code="PRJ-77", name="Склад ТОО СтройИнвест", customer_id=customer.id,
                       manager_employee_id=emp2.id, status="ACTIVE", start_date=today() - timedelta(days=5),
                       deadline=today() + timedelta(days=3), progress=0.4, is_demo=True)
    db.add(project)
    await db.flush()

    # ---- Test Scenario #1 (§52): Order AT-1001, deadline 3 days, steel tube shortage ----
    order = Order(number="AT-1001", title="Металлоконструкции для склада", customer_id=customer.id,
                  project_id=project.id, deal_id=deal.id, status="IN_PRODUCTION", priority="HIGH",
                  deadline=today() + timedelta(days=3), revenue=18_500_000, progress=0.3, is_demo=True)
    db.add(order)
    await db.flush()
    db.add(OrderItem(order_id=order.id, name="Каркас стеллажный", quantity=12, unit="шт", unit_price=850_000, is_demo=True))

    supplier = Supplier(name="ТОО МеталлСнаб", category="Металлопрокат", contact="+7 700 000 00 00",
                         rating=4.2, avg_lead_time_days=5, on_time_rate=0.8, is_demo=True)
    db.add(supplier)
    await db.flush()

    material = Material(sku="TUBE-40x40x2", name="Труба профильная 40x40x2", category="Металлопрокат",
                         unit="kg", min_stock=500, reorder_quantity=1000, lead_time_days=5, unit_cost=450,
                         preferred_supplier_id=supplier.id, is_demo=True)
    db.add(material)
    await db.flush()

    warehouse = Warehouse(code="MAIN", name="Основной склад", is_demo=True)
    db.add(warehouse)
    await db.flush()
    db.add(Stock(material_id=material.id, warehouse_id=warehouse.id, quantity=700, reserved=0,
                 last_movement_at=utcnow() - timedelta(days=10), is_demo=True))

    # incoming shipment: 500kg in 5 days — arrives AFTER the 3-day deadline => shortage per scenario
    db.add(PurchaseOrder(number="PO-9001", supplier_id=supplier.id, material_id=material.id, quantity=500,
                          unit="kg", unit_price=450, ordered_at=today(), expected_at=today() + timedelta(days=5),
                          status="ORDERED", is_demo=True))
    db.add(SupplierOffer(supplier_id=supplier.id, material_id=material.id, unit_price=460, lead_time_days=5,
                          min_quantity=100, is_demo=True))

    wc_cnc = WorkCenter(code="CNC_METAL", name="ЧПУ по металлу", department_id=dep_prod.id, sequence=1, is_demo=True)
    wc_weld = WorkCenter(code="WELDING", name="Сварочный участок", department_id=dep_prod.id, sequence=2, is_demo=True)
    wc_powder = WorkCenter(code="POWDER_COATING", name="Порошковая покраска", department_id=dep_prod.id, sequence=3,
                            slot_based=True, slot_interval_days=3, is_demo=True)
    wc_assembly = WorkCenter(code="ASSEMBLY", name="Сборка", department_id=dep_prod.id, sequence=4, is_demo=True)
    wc_qc = WorkCenter(code="QUALITY_CONTROL", name="Контроль качества", department_id=dep_prod.id, sequence=5, is_demo=True)
    wc_wh = WorkCenter(code="WAREHOUSE", name="Склад ГП", department_id=dep_wh.id, sequence=6, is_demo=True)
    wc_install = WorkCenter(code="INSTALLATION", name="Монтаж", department_id=dep_prod.id, sequence=7, is_demo=True)
    wc_wood = WorkCenter(code="WOODWORKING", name="Деревообработка", department_id=dep_prod.id, sequence=8, is_demo=True)
    wc_cncwood = WorkCenter(code="CNC_WOOD", name="ЧПУ по дереву", department_id=dep_prod.id, sequence=9, is_demo=True)
    db.add_all([wc_cnc, wc_weld, wc_powder, wc_assembly, wc_qc, wc_wh, wc_install, wc_wood, wc_cncwood])
    await db.flush()

    db.add(Workflow(code="METAL_STANDARD", name="Стандартный процесс металлоизделий", is_demo=True,
                     stages=[{"work_center": "CNC_METAL", "duration_days": 2}, {"work_center": "WELDING", "duration_days": 2},
                             {"work_center": "POWDER_COATING", "duration_days": 1}, {"work_center": "ASSEMBLY", "duration_days": 2},
                             {"work_center": "QUALITY_CONTROL", "duration_days": 1}]))

    po = ProductionOrder(number="POD-501", order_id=order.id, workflow_code="METAL_STANDARD", status="BLOCKED",
                          planned_start=today(), planned_end=today() + timedelta(days=8), progress=0.1, is_demo=True,
                          notes="Ожидает материал (труба профильная 40x40x2).")
    db.add(po)
    await db.flush()

    s1 = ProductionStage(production_order_id=po.id, work_center_id=wc_cnc.id, sequence=1, name="Раскрой ЧПУ",
                          status="BLOCKED", planned_start=today(), planned_end=today() + timedelta(days=2),
                          duration_days=2, blocked_reason="Дефицит материала: труба профильная 40x40x2 (не хватает 1100 кг).",
                          is_demo=True)
    s2 = ProductionStage(production_order_id=po.id, work_center_id=wc_weld.id, sequence=2, name="Сварка",
                          status="PLANNED", planned_start=today() + timedelta(days=2), planned_end=today() + timedelta(days=4),
                          duration_days=2, is_demo=True)
    s3 = ProductionStage(production_order_id=po.id, work_center_id=wc_powder.id, sequence=3, name="Порошковая покраска",
                          status="PLANNED", planned_start=today() + timedelta(days=4), planned_end=today() + timedelta(days=5),
                          duration_days=1, is_demo=True)
    s4 = ProductionStage(production_order_id=po.id, work_center_id=wc_assembly.id, sequence=4, name="Сборка",
                          status="PLANNED", planned_start=today() + timedelta(days=5), planned_end=today() + timedelta(days=7),
                          duration_days=2, is_demo=True)
    s5 = ProductionStage(production_order_id=po.id, work_center_id=wc_qc.id, sequence=5, name="Контроль качества",
                          status="PLANNED", planned_start=today() + timedelta(days=7), planned_end=today() + timedelta(days=8),
                          duration_days=1, is_demo=True)
    db.add_all([s1, s2, s3, s4, s5])
    await db.flush()
    for prev, nxt in ((s1, s2), (s2, s3), (s3, s4), (s4, s5)):
        db.add(StageDependency(stage_id=nxt.id, depends_on_stage_id=prev.id, is_demo=True))

    db.add(MaterialRequirement(production_order_id=po.id, stage_id=s1.id, material_id=material.id, quantity=1800,
                                unit="kg", needed_by=today() + timedelta(days=1), reserved_quantity=700, is_demo=True))

    # ---- Test Scenario #2 (§53): plan vs actual costs ----
    for category, planned_amount, actual_amount in (
        ("MATERIAL", 5_000_000, 6_100_000), ("LABOR", 2_500_000, 2_670_000),
        ("SUBCONTRACTOR", 1_000_000, 1_000_000), ("LOGISTICS", 400_000, 500_000),
        ("INSTALLATION", 200_000, 200_000), ("OTHER", 100_000, 100_000),
    ):
        db.add(Cost(order_id=order.id, kind="PLANNED", category=category, amount=planned_amount, incurred_on=today(), is_demo=True))
        db.add(Cost(order_id=order.id, kind="ACTUAL", category=category, amount=actual_amount, incurred_on=today(), is_demo=True))
    # totals: planned 9,200,000 / actual 10,570,000 matches §53 exactly

    db.add(Payment(order_id=order.id, customer_id=customer.id, direction="IN", amount=9_250_000, currency="KZT",
                    due_date=today() - timedelta(days=7), status="PENDING", counterparty=customer.name,
                    description="Аванс 50%", is_demo=True))
    db.add(Expense(category="Аренда", amount=350_000, incurred_on=today(), department_id=dep_prod.id, is_demo=True))

    # a second order, healthy, to avoid an empty-looking system
    order2 = Order(number="AT-1002", title="Ограждение territории", customer_id=customer.id, status="DELIVERED",
                    priority="NORMAL", deadline=today() - timedelta(days=2), revenue=6_000_000, progress=1.0, is_demo=True)
    db.add(order2)
    await db.flush()
    for category, planned_amount, actual_amount in (("MATERIAL", 2_000_000, 1_950_000), ("LABOR", 1_000_000, 980_000)):
        db.add(Cost(order_id=order2.id, kind="PLANNED", category=category, amount=planned_amount, incurred_on=today(), is_demo=True))
        db.add(Cost(order_id=order2.id, kind="ACTUAL", category=category, amount=actual_amount, incurred_on=today(), is_demo=True))

    db.add(Task(title="Согласовать спецификацию с клиентом", project_id=project.id, order_id=order.id,
                assignee_employee_id=emp2.id, department_id=dep_sales.id, status="OPEN", priority="HIGH",
                due_at=utcnow() - timedelta(days=1), is_demo=True))
    db.add(Task(title="Проверить остатки перед раскроем", order_id=order.id, assignee_employee_id=emp3.id,
                department_id=dep_wh.id, status="OPEN", priority="HIGH", due_at=utcnow() + timedelta(hours=6), is_demo=True))

    db.add(Document(title="Договор поставки №77 — ТОО СтройИнвест", filename="contract_77.txt",
                     stored_path="", sha256="", mime_type="text/plain", doc_type="CONTRACT",
                     classification_confidence=0.9, status="INGESTED", customer_id=customer.id, order_id=order.id,
                     text_content="Договор поставки металлоконструкций. Сумма: 18 500 000 тенге. Срок поставки: 3 дня.",
                     is_demo=True))

    db.add(Tender(title="Поставка металлоконструкций для склада ТОО Логистик", customer="ТОО Логистик",
                   source="goszakup.gov.kz (demo)", budget=25_000_000, submission_deadline=today() + timedelta(days=5),
                   status="ANALYZING", required_work_centers=["CNC_METAL", "WELDING", "POWDER_COATING"],
                   fit_score=0.8, is_demo=True))

    campaign = Campaign(name="Продвижение услуг металлообработки", channel="Instagram", status="ACTIVE",
                         budget=300_000, spent=120_000, start_date=today() - timedelta(days=15), leads_generated=6, is_demo=True)
    db.add(campaign)
    await db.flush()
    db.add(Lead(name="Марат И.", company="ИП Марат", source="instagram", campaign_id=campaign.id, status="NEW",
                received_at=utcnow() - timedelta(days=1), is_demo=True))

    await db.flush()
    return {
        "departments": 3, "employees": 3, "customers": 1, "deals": 2, "projects": 1,
        "orders": 2, "materials": 1, "suppliers": 1, "production_orders": 1, "stages": 5,
        "tenders": 1, "campaigns": 1,
    }
