from typing import AsyncGenerator

from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import DeclarativeBase

from app.core.config import settings


# Keep the connection pool small for Neon/serverless PostgreSQL.
# The dashboard makes several requests simultaneously, so a smaller
# pool prevents unnecessary connection pressure.
import sys
from sqlalchemy.pool import NullPool

engine_kwargs = {
    "echo": settings.DEBUG,
    "connect_args": {
        "timeout": 30,
    },
}

if "pytest" in sys.modules:
    engine_kwargs["poolclass"] = NullPool
else:
    engine_kwargs["pool_pre_ping"] = True
    engine_kwargs["pool_size"] = 5
    engine_kwargs["max_overflow"] = 2
    engine_kwargs["pool_recycle"] = 300

engine = create_async_engine(
    settings.DATABASE_URL,
    **engine_kwargs,
)


async_session_factory = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


class Base(DeclarativeBase):
    pass


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    async with async_session_factory() as session:
        try:
            yield session
        except Exception:
            await session.rollback()
            raise