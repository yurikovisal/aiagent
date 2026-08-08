from fastapi import APIRouter

router = APIRouter()


@router.get("/status")
async def connectors_status():
    """1С / WMS / Excel / Bitrix / IMAP / Telegram — фаза 3."""
    return {"ready": False, "phase": 3, "connectors": []}
