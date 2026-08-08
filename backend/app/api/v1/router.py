from fastapi import APIRouter

from app.api.v1 import admin, chat, connectors, meetings, production, vision, warehouse

api_router = APIRouter()
api_router.include_router(chat.router, prefix="/chat", tags=["chat"])
api_router.include_router(warehouse.router, prefix="/warehouse", tags=["warehouse"])
api_router.include_router(production.router, prefix="/production", tags=["production"])
api_router.include_router(vision.router, prefix="/vision", tags=["vision"])
api_router.include_router(meetings.router, prefix="/meetings", tags=["meetings"])
api_router.include_router(connectors.router, prefix="/connectors", tags=["connectors"])
api_router.include_router(admin.router, prefix="/admin", tags=["admin"])
