"""Async SQLAlchemy engine and session factory."""

from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from app.core.config import Settings

_engine: AsyncEngine | None = None
_session_factory: async_sessionmaker[AsyncSession] | None = None


def init_db(settings: Settings) -> None:
    """Create async engine and session factory."""
    global _engine, _session_factory

    _engine = create_async_engine(
        settings.async_database_url,
        echo=settings.debug,
        pool_pre_ping=True,
    )
    _session_factory = async_sessionmaker(
        bind=_engine,
        class_=AsyncSession,
        expire_on_commit=False,
        autoflush=False,
        autocommit=False,
    )


def get_engine() -> AsyncEngine:
    if _engine is None:
        raise RuntimeError("Database engine is not initialized. Call init_db() first.")
    return _engine


def get_session_factory() -> async_sessionmaker[AsyncSession]:
    if _session_factory is None:
        raise RuntimeError("Session factory is not initialized. Call init_db() first.")
    return _session_factory


async def dispose_db() -> None:
    global _engine, _session_factory
    if _engine is not None:
        await _engine.dispose()
    _engine = None
    _session_factory = None


async def get_async_session() -> AsyncGenerator[AsyncSession, None]:
    """Yield an async database session with commit/rollback handling."""
    factory = get_session_factory()
    async with factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
