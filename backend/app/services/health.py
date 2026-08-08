import logging
from typing import Any

import httpx
from redis.asyncio import Redis
from sqlalchemy import text

from app.core.config import get_settings
from app.core.deps import engine

logger = logging.getLogger(__name__)


async def check_dependencies() -> dict[str, Any]:
    settings = get_settings()
    checks: dict[str, dict[str, Any]] = {}

    # PostgreSQL
    try:
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
        checks["postgres"] = {"status": "up"}
    except Exception as exc:  # noqa: BLE001 — health must never crash
        logger.warning("postgres health failed: %s", exc)
        checks["postgres"] = {"status": "down", "error": str(exc)}

    # Redis
    try:
        redis = Redis.from_url(settings.redis_url, decode_responses=True)
        pong = await redis.ping()
        await redis.aclose()
        checks["redis"] = {"status": "up" if pong else "down"}
    except Exception as exc:  # noqa: BLE001
        logger.warning("redis health failed: %s", exc)
        checks["redis"] = {"status": "down", "error": str(exc)}

    # MinIO
    try:
        scheme = "https" if settings.minio_secure else "http"
        url = f"{scheme}://{settings.minio_endpoint}/minio/health/live"
        async with httpx.AsyncClient(timeout=3.0) as client:
            resp = await client.get(url)
        checks["minio"] = {"status": "up" if resp.status_code == 200 else "down"}
    except Exception as exc:  # noqa: BLE001
        logger.warning("minio health failed: %s", exc)
        checks["minio"] = {"status": "down", "error": str(exc)}

    # Ollama (optional)
    try:
        async with httpx.AsyncClient(timeout=2.0) as client:
            resp = await client.get(f"{settings.ollama_base_url}/api/tags")
        checks["ollama"] = {
            "status": "up" if resp.status_code == 200 else "down",
            "optional": True,
        }
    except Exception as exc:  # noqa: BLE001
        checks["ollama"] = {"status": "down", "optional": True, "error": str(exc)}

    required_ok = all(
        checks[name]["status"] == "up" for name in ("postgres", "redis", "minio")
    )
    return {"ok": required_ok, "checks": checks}
