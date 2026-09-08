"""MEZA FastAPI application factory."""

from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from meza.api.errors import install_error_handlers
from meza.api.middleware import RateLimitMiddleware, RequestContextMiddleware, SecurityHeadersMiddleware
from meza.api.v1 import (
    agents as agents_api,
    approvals as approvals_api,
    auth as auth_api,
    documents as documents_api,
    finance as finance_api,
    imports as imports_api,
    inbox as inbox_api,
    inventory as inventory_api,
    memory as memory_api,
    meza_chat as meza_chat_api,
    org as org_api,
    orders as orders_api,
    procurement as procurement_api,
    production as production_api,
    risks as risks_api,
    search as search_api,
    system as system_api,
    users as users_api,
)
from meza.core.config import get_settings
from meza.core.db import dispose_engine, get_engine
from meza.core.logging import configure_logging


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = get_settings()
    configure_logging(settings.log_level)
    get_engine()  # warm up the pool
    yield
    await dispose_engine()


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(title="MEZA API", version="0.1.0", lifespan=lifespan, docs_url="/api/docs", redoc_url=None)

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origin_list,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.add_middleware(RateLimitMiddleware)
    app.add_middleware(SecurityHeadersMiddleware)
    app.add_middleware(RequestContextMiddleware)

    install_error_handlers(app)

    for router in (
        auth_api.router, meza_chat_api.router, orders_api.router, production_api.router,
        inventory_api.router, procurement_api.router, finance_api.router, documents_api.router,
        risks_api.router, approvals_api.router, agents_api.router, system_api.router,
        imports_api.router, inbox_api.router, search_api.router, org_api.router, memory_api.router, users_api.router,
    ):
        app.include_router(router)

    @app.get("/")
    async def root():
        return {"name": "MEZA", "version": "0.1.0", "docs": "/api/docs"}

    return app


app = create_app()
