from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings
from app.core.database import create_database_engine, create_session_factory


async def test_create_database_engine_uses_postgresql_asyncpg() -> None:
    settings = Settings(
        app_env="test",
        database_url="postgresql+asyncpg://user:password@localhost/database",
    )

    engine = create_database_engine(settings)

    assert engine.dialect.name == "postgresql"
    assert engine.dialect.driver == "asyncpg"
    await engine.dispose()


async def test_session_factory_creates_async_session() -> None:
    settings = Settings(
        app_env="test",
        database_url="postgresql+asyncpg://user:password@localhost/database",
    )
    engine = create_database_engine(settings)
    session_factory = create_session_factory(engine)

    async with session_factory() as session:
        assert isinstance(session, AsyncSession)

    await engine.dispose()

