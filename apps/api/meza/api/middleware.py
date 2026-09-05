"""Request ID, structured access logging, rate limiting, and security headers."""

from __future__ import annotations

import time
from collections import defaultdict, deque

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

from meza.core.config import get_settings
from meza.core.logging import get_logger, request_id_var, user_id_var
from meza.core.utils import new_id

logger = get_logger("meza.access")


class RequestContextMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        rid = new_id()
        request_id_var.set(rid)
        user_id_var.set(None)
        started = time.perf_counter()
        response: Response = await call_next(request)
        duration_ms = int((time.perf_counter() - started) * 1000)
        response.headers["X-Request-ID"] = rid
        logger.info(
            f"{request.method} {request.url.path} -> {response.status_code}",
            extra={"duration_ms": duration_ms, "request_id": rid, "path": request.url.path, "method": request.method},
        )
        return response


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["Referrer-Policy"] = "same-origin"
        response.headers["Permissions-Policy"] = "geolocation=(), microphone=(), camera=()"
        return response


class RateLimitMiddleware(BaseHTTPMiddleware):
    """Simple in-process fixed-window limiter, keyed by client IP. Good enough for a single-node
    local deployment; swap for a Redis-backed limiter if MEZA is ever scaled out."""

    def __init__(self, app):
        super().__init__(app)
        self._hits: dict[str, deque] = defaultdict(deque)

    async def dispatch(self, request: Request, call_next):
        settings = get_settings()
        limit = settings.rate_limit_per_minute
        if limit <= 0 or request.url.path.startswith("/api/v1/system/health"):
            return await call_next(request)
        key = request.client.host if request.client else "unknown"
        now = time.time()
        window = self._hits[key]
        while window and now - window[0] > 60:
            window.popleft()
        if len(window) >= limit:
            from fastapi.responses import JSONResponse

            return JSONResponse({"detail": "Слишком много запросов. Попробуйте позже."}, status_code=429)
        window.append(now)
        return await call_next(request)
