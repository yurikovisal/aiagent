from fastapi import APIRouter

router = APIRouter()


@router.get("/status")
async def chat_status():
    """Заглушка фазы 0. Streaming-чат — фаза 1."""
    return {"ready": False, "phase": 1, "message": "Chat streaming not implemented yet"}
