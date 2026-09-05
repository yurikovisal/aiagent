from __future__ import annotations

import shutil

from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from meza.core.config import get_settings
from meza.core.db import get_db
from meza.llm.factory import get_llm_provider

router = APIRouter(prefix="/api/v1/system", tags=["system"])


@router.get("/health")
async def health(db: AsyncSession = Depends(get_db)):
    settings = get_settings()
    checks: dict[str, dict] = {}

    try:
        await db.execute(text("SELECT 1"))
        checks["database"] = {"status": "ok"}
    except Exception as exc:  # noqa: BLE001
        checks["database"] = {"status": "error", "error": str(exc)}

    checks["redis"] = {"status": "not_configured"} if not settings.redis_url else {"status": "ok"}

    provider = get_llm_provider()
    if provider:
        checks["ollama"] = await provider.health()
    else:
        checks["ollama"] = {"status": "not_configured"}

    try:
        usage = shutil.disk_usage(settings.upload_path.parent)
        checks["storage"] = {"status": "ok", "free_gb": round(usage.free / 1e9, 1)}
    except Exception as exc:  # noqa: BLE001
        checks["storage"] = {"status": "error", "error": str(exc)}

    overall = "ok" if all(c["status"] in ("ok", "not_configured") for c in checks.values()) else "degraded"
    return {"status": overall, "checks": checks, "app_env": settings.app_env}
