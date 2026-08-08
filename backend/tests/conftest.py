import os

import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

# tests use sqlite + mock LLM
os.environ["DATABASE_URL"] = "sqlite+aiosqlite:///:memory:"
os.environ["LLM_MOCK"] = "true"
os.environ["API_SECRET_KEY"] = "test-secret-key-for-jwt-hs256"

from app.core.config import get_settings  # noqa: E402

get_settings.cache_clear()

from app.core import deps  # noqa: E402
from app.main import create_app  # noqa: E402
from app.models import Base  # noqa: E402


@pytest_asyncio.fixture
async def db_engine():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    deps.engine = engine
    deps.SessionLocal = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)
    yield engine
    await engine.dispose()


@pytest_asyncio.fixture
async def client(db_engine):
    app = create_app()

    async def _get_db():
        async with deps.SessionLocal() as session:
            yield session

    app.dependency_overrides[deps.get_db] = _get_db
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac
    app.dependency_overrides.clear()
