from fastapi import APIRouter

router = APIRouter()


@router.get("/status")
async def production_status():
    """План-факт / OEE / capacity — фаза 3."""
    return {"ready": False, "phase": 3}
