"""Integration coverage for the Alembic migrations and the development seed."""

import asyncio
import os
import subprocess
from decimal import Decimal
from pathlib import Path

from sqlalchemy import func, select, text
from sqlalchemy.ext.asyncio import AsyncEngine, create_async_engine

from app.core.config import Settings
from app.core.database import create_session_factory
from app.models import Household, Inventory, InventoryItem, User
from app.scripts.seed import seed_database

BACKEND_DIR = Path(__file__).resolve().parents[2]
MIGRATION_HEAD = "20260720_0002"
EXPECTED_TABLES = {
    "households",
    "users",
    "household_members",
    "inventory_items",
    "inventory",
    "inventory_events",
    "audit_logs",
    "alembic_version",
}


async def test_alembic_migrations_apply_to_empty_database(
    integration_settings: Settings,
) -> None:
    url = integration_settings.test_database_url
    assert url is not None
    engine = create_async_engine(url, connect_args={"statement_cache_size": 0})
    try:
        async with engine.begin() as connection:
            await connection.execute(text("DROP SCHEMA IF EXISTS public CASCADE"))
            await connection.execute(text("CREATE SCHEMA public"))

        completed = await asyncio.to_thread(
            subprocess.run,
            ["uv", "run", "alembic", "upgrade", "head"],
            cwd=str(BACKEND_DIR),
            env={**os.environ, "DATABASE_URL": url},
            capture_output=True,
            text=True,
        )
        assert completed.returncode == 0, completed.stderr

        async with engine.connect() as connection:
            version = await connection.scalar(
                text("SELECT version_num FROM alembic_version")
            )
            table_rows = await connection.scalars(
                text(
                    "SELECT table_name FROM information_schema.tables "
                    "WHERE table_schema = 'public'"
                )
            )
            tables = set(table_rows.all())

        assert version == MIGRATION_HEAD
        assert EXPECTED_TABLES <= tables
    finally:
        async with engine.begin() as connection:
            await connection.execute(text("DROP SCHEMA IF EXISTS public CASCADE"))
            await connection.execute(text("CREATE SCHEMA public"))
        await engine.dispose()


async def test_seed_is_idempotent(integration_engine: AsyncEngine) -> None:
    session_factory = create_session_factory(integration_engine)

    first = await seed_database(session_factory)
    second = await seed_database(session_factory)

    assert first.households_created == 1
    assert first.users_created == 1
    assert first.items_created == 5
    assert first.snapshots_created == 5
    assert second.households_created == 0
    assert second.users_created == 0
    assert second.items_created == 0
    assert second.snapshots_created == 0

    async with session_factory() as session:
        households = await session.scalar(select(func.count()).select_from(Household))
        users = await session.scalar(select(func.count()).select_from(User))
        items = await session.scalar(select(func.count()).select_from(InventoryItem))
        snapshots = await session.scalar(select(func.count()).select_from(Inventory))
        zero_snapshots = await session.scalar(
            select(func.count())
            .select_from(Inventory)
            .where(Inventory.quantity == Decimal("0"))
        )

    assert households == 1
    assert users == 1
    assert items == 5
    assert snapshots == 5
    assert zero_snapshots == 5
