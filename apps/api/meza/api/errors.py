from __future__ import annotations

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from meza.core.errors import MezaError


def install_error_handlers(app: FastAPI) -> None:
    @app.exception_handler(MezaError)
    async def handle_meza_error(request: Request, exc: MezaError):
        return JSONResponse({"code": exc.code, "message": exc.message, "details": exc.details}, status_code=exc.status_code)
