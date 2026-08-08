from fastapi import APIRouter

router = APIRouter()


@router.get("/status")
async def admin_status():
    """Админ-эндпоинты — фаза 1+."""
    return {"ready": False, "phase": 1}
