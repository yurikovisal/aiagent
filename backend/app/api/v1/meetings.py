from fastapi import APIRouter

router = APIRouter()


@router.get("/status")
async def meetings_status():
    """Протоколы собраний — фаза 6."""
    return {"ready": False, "phase": 6}
