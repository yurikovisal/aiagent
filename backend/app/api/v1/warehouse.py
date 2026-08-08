from fastapi import APIRouter

router = APIRouter()


@router.get("/status")
async def warehouse_status():
    """Инструменты склада (stock_balance и др.) — фаза 3."""
    return {"ready": False, "phase": 3}
