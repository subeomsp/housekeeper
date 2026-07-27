from collections.abc import AsyncIterator

import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import (
    AsyncConnection,
    AsyncEngine,
    AsyncSession,
    create_async_engine,
)

import app.models  # noqa: F401  (register every model on Base.metadata)
from app.core.config import Settings
from app.core.database import create_session_factory
from app.models.base import Base


async def _reset_public_schema(connection: AsyncConnection) -> None:
    """Drop and recreate the public schema so each test starts empty.

    Resetting the whole schema (rather than Base.metadata.drop_all) is immune to
    foreign-key ordering and to leftover tables from an interrupted run.
    """
    await connection.execute(text("DROP SCHEMA IF EXISTS public CASCADE"))
    await connection.execute(text("CREATE SCHEMA public"))


@pytest.fixture
def integration_settings() -> Settings:
    """Settings for integration tests; skips the suite when no test DB is set."""
    settings = Settings(app_env="test")
    if not settings.test_database_url:
        pytest.skip("TEST_DATABASE_URL is not set; skipping integration tests")
    return settings


@pytest.fixture
async def integration_engine(
    integration_settings: Settings,
) -> AsyncIterator[AsyncEngine]:
    """A real PostgreSQL engine on a freshly built, empty schema.

    The schema is reset and rebuilt before the test and reset again afterwards.
    ``statement_cache_size=0`` keeps asyncpg compatible with the Neon connection
    pooler under concurrent connections.
    """
    url = integration_settings.test_database_url
    assert url is not None
    engine = create_async_engine(
        url,
        pool_pre_ping=True,
        connect_args={"statement_cache_size": 0},
    )
    async with engine.begin() as connection:
        await _reset_public_schema(connection)
        await connection.run_sync(Base.metadata.create_all)
    try:
        yield engine
    finally:
        async with engine.begin() as connection:
            await _reset_public_schema(connection)
        await engine.dispose()


@pytest.fixture
async def db_session(integration_engine: AsyncEngine) -> AsyncIterator[AsyncSession]:
    """A session on the integration engine; services manage their own transactions."""
    session_factory = create_session_factory(integration_engine)
    async with session_factory() as session:
        yield session
