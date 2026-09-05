from __future__ import annotations

import os
import tempfile

import pytest_asyncio

_tmp_db = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
os.environ.setdefault("DATABASE_URL", f"sqlite+aiosqlite:///{_tmp_db.name}")
os.environ.setdefault("SECRET_KEY", "test-secret")
os.environ.setdefault("LLM_PROVIDER", "none")

from meza.core.db import dispose_engine, get_engine, get_session_factory  # noqa: E402
from meza.models import Base  # noqa: E402


@pytest_asyncio.fixture
async def db_session():
    engine = get_engine()
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    factory = get_session_factory()
    async with factory() as session:
        yield session
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await dispose_engine()
