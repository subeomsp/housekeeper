from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession


async def test_database_roundtrip(db_session: AsyncSession) -> None:
    """The test database is reachable and the schema was created."""
    result = await db_session.scalar(text("SELECT 1"))
    assert result == 1


async def test_schema_tables_exist(db_session: AsyncSession) -> None:
    """The Phase 1 tables are present after the harness builds the schema."""
    tables = await db_session.scalars(
        text(
            "SELECT table_name FROM information_schema.tables "
            "WHERE table_schema = 'public'"
        )
    )
    names = set(tables.all())
    assert {
        "households",
        "users",
        "household_members",
        "inventory_items",
        "inventory",
        "inventory_events",
        "audit_logs",
    } <= names
