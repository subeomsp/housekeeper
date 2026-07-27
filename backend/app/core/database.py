from collections.abc import AsyncIterator

from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from app.core.config import Settings, get_settings


def create_database_engine(settings: Settings | None = None) -> AsyncEngine:
    resolved_settings = settings or get_settings()
    return create_async_engine(
        resolved_settings.database_url,
        echo=resolved_settings.database_echo,
        pool_pre_ping=True,
    )


def create_session_factory(engine: AsyncEngine) -> async_sessionmaker[AsyncSession]:
    return async_sessionmaker(
        bind=engine,
        class_=AsyncSession,
        expire_on_commit=False,
        autoflush=False,
    )


engine = create_database_engine()
async_session_factory = create_session_factory(engine)


async def get_db_session() -> AsyncIterator[AsyncSession]:
    async with async_session_factory() as session:
        yield session

