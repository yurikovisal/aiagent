from fastapi import APIRouter

router = APIRouter()


@router.get("/status")
async def vision_status():
    """VLM / OCR / YOLO — фаза 4."""
    return {"ready": False, "phase": 4}
