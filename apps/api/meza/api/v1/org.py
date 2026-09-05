from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from meza.api.deps import require_permission
from meza.core.db import get_db
from meza.core.rbac import Permission
from meza.models import Customer, Deal, Department, Employee, Project, Task

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
