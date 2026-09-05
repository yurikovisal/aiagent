from __future__ import annotations

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from meza.api.deps import get_current_user, require_permission
from meza.core.config import get_settings
from meza.core.db import get_db
from meza.core.rbac import Permission
from meza.core.utils import utcnow
from meza.models import ImportJob, User
from meza.services import import_center

router = APIRouter(prefix="/api/v1/imports", tags=["imports"])


@router.post("/upload")
async def upload(file: UploadFile = File(...), target_entity: str = Form(...),
                  user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    from meza.core.rbac import has_permission

    if not has_permission(user.role, Permission.IMPORT_DATA):
        raise HTTPException(403, "Недостаточно прав для импорта данных.")
    filename = file.filename or "upload"
    ext = filename.rsplit(".", 1)[-1].lower()
    file_type = {"csv": "csv", "xlsx": "xlsx", "json": "json"}.get(ext)
    if not file_type:
        raise HTTPException(422, "Поддерживаются только CSV, XLSX, JSON.")
    content = await file.read()
    settings = get_settings()
    settings.upload_path.mkdir(parents=True, exist_ok=True)
    stored_path = settings.upload_path / f"import_{utcnow().timestamp():.0f}_{filename}"
    stored_path.write_bytes(content)
    columns = import_center.detect_columns(file_type, content)
    mapping = import_center.suggest_mapping(columns, target_entity)
    rows = import_center.read_rows(file_type, content)
    job = ImportJob(
        filename=filename, stored_path=str(stored_path), file_type=file_type, target_entity=target_entity,
        detected_columns=columns, suggested_mapping=mapping, mapping=mapping, preview=rows[:10],
        row_count=len(rows), status="MAPPED", created_by=user.id, created_at=utcnow(),
    )
    validation = import_center.validate_rows(rows, mapping, target_entity)
    job.validation = validation
    job.status = "VALIDATED" if validation["valid"] else "MAPPED"
    db.add(job)
    await db.commit()
    return job.as_dict()


class MappingUpdate(BaseModel):
    mapping: dict


@router.post("/{job_id}/mapping")
async def update_mapping(job_id: int, payload: MappingUpdate, db: AsyncSession = Depends(get_db),
                          _=Depends(require_permission(Permission.IMPORT_DATA))):
    job = await db.get(ImportJob, job_id)
    if not job:
        raise HTTPException(404, "Импорт не найден.")
    job.mapping = payload.mapping
    rows = import_center.read_rows(job.file_type, open(job.stored_path, "rb").read())
    job.validation = import_center.validate_rows(rows, job.mapping, job.target_entity)
    job.status = "VALIDATED" if job.validation["valid"] else "MAPPED"
    await db.commit()
    return job.as_dict()


@router.post("/{job_id}/confirm")
async def confirm_import(job_id: int, db: AsyncSession = Depends(get_db),
                          user: User = Depends(get_current_user)):
    from meza.core.rbac import has_permission

    if not has_permission(user.role, Permission.IMPORT_DATA):
        raise HTTPException(403, "Недостаточно прав.")
    job = await db.get(ImportJob, job_id)
    if not job:
        raise HTTPException(404, "Импорт не найден.")
    if job.status != "VALIDATED":
        raise HTTPException(422, "Импорт не прошёл валидацию.")
    imported = await import_center.apply_import(db, job)
    job.imported_count = imported
    job.status = "IMPORTED"
    await db.commit()
    return job.as_dict()


@router.get("/{job_id}")
async def get_job(job_id: int, db: AsyncSession = Depends(get_db), _=Depends(require_permission(Permission.IMPORT_DATA))):
    job = await db.get(ImportJob, job_id)
    return job.as_dict() if job else {"error": "not_found"}
