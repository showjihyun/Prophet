"""Async SQLAlchemy engine setup.
SPEC: docs/spec/08_DB_SPEC.md
"""
import sys
from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase
from sqlalchemy.pool import NullPool

from app.config import settings


# Pytest creates a fresh event loop per test by default, which invalidates
# any connection left in the pool from a previous test ("'NoneType' object
# has no attribute 'send'"). We detect test mode via ``sys.modules`` and
# switch to ``NullPool`` so every session opens a fresh connection and
# closes it cleanly when the session exits. Production keeps the default
# pool + ``pool_pre_ping=True`` for fast reuse.
_engine_kwargs: dict = {"echo": False}
if "pytest" in sys.modules:
    _engine_kwargs["poolclass"] = NullPool
else:
    _engine_kwargs["pool_pre_ping"] = True

engine = create_async_engine(settings.database_url, **_engine_kwargs)
async_session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


class Base(DeclarativeBase):
    pass


async def get_session() -> AsyncGenerator[AsyncSession, None]:
    async with async_session() as session:
        yield session
