"""
Database Configuration
=======================
Async SQLAlchemy engine setup with PostgreSQL connection pooling.
Supports both PostgreSQL (production) and SQLite (development/testing).

Connection pooling ensures efficient resource usage under concurrent load:
- pool_size: Number of persistent connections maintained
- max_overflow: Additional connections allowed during traffic spikes
- pool_recycle: Prevents stale connections from accumulating
"""

from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy.orm import DeclarativeBase
from app.core.config import settings

# Convert standard DB URL to async driver format
_raw_url = settings.DATABASE_URL

if _raw_url.startswith("postgresql://"):
    DATABASE_URL = _raw_url.replace("postgresql://", "postgresql+asyncpg://")
elif _raw_url.startswith("sqlite:///"):
    DATABASE_URL = _raw_url.replace("sqlite:///", "sqlite+aiosqlite:///")
else:
    DATABASE_URL = _raw_url

# Engine configuration — optimized for PostgreSQL with connection pooling
_engine_kwargs = {"echo": False, "pool_pre_ping": True}

if DATABASE_URL.startswith("postgresql"):
    _engine_kwargs.update({
        "pool_size": 10,
        "max_overflow": 20,
        "pool_timeout": 30,
        "pool_recycle": 1800,
    })
elif DATABASE_URL.startswith("sqlite"):
    _engine_kwargs["connect_args"] = {"check_same_thread": False}

engine = create_async_engine(DATABASE_URL, **_engine_kwargs)

AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


class Base(DeclarativeBase):
    """Base class for all SQLAlchemy ORM models."""
    pass


async def get_db():
    """
    Dependency injection for database sessions.
    Used with FastAPI's Depends() to provide a session per request.
    Automatically commits on success, rolls back on error.
    """
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
