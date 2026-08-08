from arq.connections import RedisSettings

from app.core.config import get_settings


async def startup(ctx: dict) -> None:
    ctx["settings"] = get_settings()


async def shutdown(ctx: dict) -> None:
    _ = ctx


class WorkerSettings:
    functions: list = []
    on_startup = startup
    on_shutdown = shutdown
    redis_settings = RedisSettings.from_dsn(get_settings().redis_url)
