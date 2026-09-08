from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from meza.api.deps import require_permission
from meza.core.db import get_db
from meza.core.rbac import Permission
from meza.models import KPI, Attendance, Customer, Deal, Department, Employee, EmployeeReport, Project, Task

router = APIRouter(prefix="/api/v1", tags=["org"])


@router.get("/departments")
async def list_departments(db: AsyncSession = Depends(get_db), _=Depends(require_permission(Permission.READ_EMPLOYEES))):
    rows = (await db.execute(select(Department))).scalars().all()
    return [r.as_dict() for r in rows]


@router.get("/employees")
async def list_employees(department_id: int | None = None, db: AsyncSession = Depends(get_db),
                          _=Depends(require_permission(Permission.READ_EMPLOYEES))):
    q = select(Employee)
    if department_id:
        q = q.where(Employee.department_id == department_id)
    rows = (await db.execute(q)).scalars().all()
    return [r.as_dict() for r in rows]


@router.get("/employees/{employee_id}")
async def get_employee(employee_id: int, db: AsyncSession = Depends(get_db), _=Depends(require_permission(Permission.READ_EMPLOYEES))):
    """§22: department workload + individual detail, using only transparently collected data
    (attendance, KPI, self-submitted reports) — no covert tracking."""
    employee = await db.get(Employee, employee_id)
    if not employee:
        return {"error": "not_found"}
    attendance = (await db.execute(
        select(Attendance).where(Attendance.employee_id == employee_id).order_by(Attendance.day.desc()).limit(30)
    )).scalars().all()
    kpis = (await db.execute(
        select(KPI).where(KPI.employee_id == employee_id).order_by(KPI.period.desc()).limit(12)
    )).scalars().all()
    reports = (await db.execute(
        select(EmployeeReport).where(EmployeeReport.employee_id == employee_id).order_by(EmployeeReport.submitted_at.desc()).limit(10)
    )).scalars().all()
    tasks = (await db.execute(
        select(Task).where(Task.assignee_employee_id == employee_id, Task.status != "DONE")
    )).scalars().all()
    present_days = sum(1 for a in attendance if a.status == "PRESENT")
    attendance_rate = round(present_days / len(attendance), 3) if attendance else None
    return {
        "employee": employee.as_dict(),
        "attendance": [a.as_dict() for a in attendance],
        "attendance_rate_30d": attendance_rate,
        "kpis": [k.as_dict() for k in kpis],
        "reports": [r.as_dict() for r in reports],
        "open_tasks": [t.as_dict() for t in tasks],
    }


@router.get("/deals")
async def list_deals(stage: str | None = None, db: AsyncSession = Depends(get_db), _=Depends(require_permission(Permission.READ_SALES))):
    q = select(Deal)
    if stage:
        q = q.where(Deal.stage == stage)
    rows = (await db.execute(q.order_by(Deal.created_at.desc()))).scalars().all()
    return [r.as_dict() for r in rows]


@router.get("/customers")
async def list_customers(db: AsyncSession = Depends(get_db), _=Depends(require_permission(Permission.READ_SALES))):
    rows = (await db.execute(select(Customer))).scalars().all()
    return [r.as_dict() for r in rows]


@router.get("/projects")
async def list_projects(db: AsyncSession = Depends(get_db), _=Depends(require_permission(Permission.READ_PROJECTS))):
    rows = (await db.execute(select(Project))).scalars().all()
    return [r.as_dict() for r in rows]


@router.get("/projects/{project_id}/delay-analysis")
async def project_delay_analysis(project_id: int, db: AsyncSession = Depends(get_db), _=Depends(require_permission(Permission.READ_PROJECTS))):
    """§19 causal chain: why is this project actually delayed, tracing back through task
    dependencies to the root cause rather than just listing every overdue task."""
    from meza.core.utils import utcnow
    from meza.rules.projects import TaskNode, analyze_project_delay

    rows = (await db.execute(select(Task).where(Task.project_id == project_id))).scalars().all()
    if not rows:
        return {"root_cause": None, "chain": [], "overdue_task_count": 0, "blocked_task_count": 0}
    nodes = [TaskNode(t.id, t.title, t.status, t.due_at, t.depends_on_task_id) for t in rows]
    return analyze_project_delay(nodes, utcnow()).as_dict()


@router.get("/tasks")
async def list_tasks(status: str | None = None, project_id: int | None = None, db: AsyncSession = Depends(get_db),
                      _=Depends(require_permission(Permission.READ_PROJECTS))):
    q = select(Task)
    if status:
        q = q.where(Task.status == status)
    if project_id:
        q = q.where(Task.project_id == project_id)
    rows = (await db.execute(q.order_by(Task.due_at.asc().nullslast()))).scalars().all()
    return [r.as_dict() for r in rows]


@router.get("/audit-log")
async def audit_log(limit: int = 100, db: AsyncSession = Depends(get_db), _=Depends(require_permission(Permission.READ_AUDIT))):
    from meza.models import AuditLog
    rows = (await db.execute(select(AuditLog).order_by(AuditLog.timestamp.desc()).limit(limit))).scalars().all()
    return [r.as_dict() for r in rows]
