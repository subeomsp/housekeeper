"""Integration tests exercising the real PostgreSQL transaction and lock paths.

These cover behaviour the unit tests (fake repositories) cannot: atomic commit,
rollback on failure, row locking under concurrency, foreign keys, and Snapshot
rebuild against the actual event ledger.
"""

import asyncio
from decimal import Decimal
from uuid import UUID

import pytest
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession

from app.core.database import create_session_factory
from app.core.exceptions import AppError
from app.models import AuditLog, Inventory, InventoryEvent, InventoryItem
from app.models.household import Household
from app.models.user import User
from app.repositories.audit_log_repository import AuditLogRepository
from app.repositories.inventory_event_repository import InventoryEventRepository
from app.repositories.inventory_item_repository import InventoryItemRepository
from app.repositories.inventory_repository import InventoryRepository
from app.schemas.inventory_event import (
    InventoryEventCorrectionRequest,
    InventoryEventCreate,
)
from app.schemas.inventory_item import InventoryItemCreate
from app.services.inventory_item_service import InventoryItemService
from app.services.inventory_service import InventoryService

HOUSEHOLD_ID = UUID("00000000-0000-4000-8000-0000000000a1")
OTHER_HOUSEHOLD_ID = UUID("00000000-0000-4000-8000-0000000000a2")
USER_ID = UUID("00000000-0000-4000-8000-0000000000b1")


def item_service() -> InventoryItemService:
    return InventoryItemService(InventoryItemRepository(), AuditLogRepository())


def inventory_service() -> InventoryService:
    return InventoryService(
        InventoryRepository(),
        InventoryEventRepository(),
        AuditLogRepository(),
    )


async def seed_household(session: AsyncSession, *, household_id: UUID, name: str) -> None:
    async with session.begin():
        session.add(Household(id=household_id, name=name))


async def create_item(
    session: AsyncSession,
    *,
    household_id: UUID = HOUSEHOLD_ID,
    name: str = "우유",
    unit: str = "개",
) -> UUID:
    view = await item_service().create_item(
        session,
        household_id=household_id,
        user_id=USER_ID,
        data=InventoryItemCreate(name=name, default_unit=unit, category=None),
    )
    return view.id


@pytest.fixture
async def base(db_session: AsyncSession) -> tuple[UUID, UUID]:
    async with db_session.begin():
        db_session.add(Household(id=HOUSEHOLD_ID, name="우리 집"))
        db_session.add(User(id=USER_ID, nickname="테스트 사용자"))
    return HOUSEHOLD_ID, USER_ID


async def test_create_item_persists_item_snapshot_and_audit(
    db_session: AsyncSession,
    base: tuple[UUID, UUID],
) -> None:
    item_id = await create_item(db_session)

    item = await db_session.scalar(
        select(InventoryItem).where(InventoryItem.id == item_id)
    )
    snapshot_quantity = await db_session.scalar(
        select(Inventory.quantity).where(Inventory.item_id == item_id)
    )
    audit_count = await db_session.scalar(
        select(func.count())
        .select_from(AuditLog)
        .where(
            AuditLog.target_id == item_id,
            AuditLog.action == "inventory_item_created",
        )
    )

    assert item is not None
    assert item.name == "우유"
    assert snapshot_quantity == Decimal("0")
    assert audit_count == 1


async def test_duplicate_item_name_rejected(
    db_session: AsyncSession,
    base: tuple[UUID, UUID],
) -> None:
    await create_item(db_session, name="우유")

    with pytest.raises(AppError) as captured:
        await create_item(db_session, name="우유")

    assert captured.value.code == "DUPLICATE_ITEM_NAME"
    item_count = await db_session.scalar(
        select(func.count()).select_from(InventoryItem)
    )
    assert item_count == 1


async def test_event_and_snapshot_committed_atomically(
    db_session: AsyncSession,
    base: tuple[UUID, UUID],
) -> None:
    item_id = await create_item(db_session)

    result = await inventory_service().create_inventory_event(
        db_session,
        household_id=HOUSEHOLD_ID,
        user_id=USER_ID,
        data=InventoryEventCreate(
            item_id=item_id,
            event_type="stock_in",
            quantity=Decimal("5"),
            unit="개",
        ),
    )

    assert result.current_quantity == Decimal("5")
    snapshot_quantity = await db_session.scalar(
        select(Inventory.quantity).where(Inventory.item_id == item_id)
    )
    signed = await db_session.scalar(
        select(InventoryEvent.signed_quantity).where(
            InventoryEvent.item_id == item_id
        )
    )
    assert snapshot_quantity == Decimal("5")
    assert signed == Decimal("5")


async def test_negative_stock_out_rolls_back_without_writes(
    db_session: AsyncSession,
    base: tuple[UUID, UUID],
) -> None:
    item_id = await create_item(db_session)

    with pytest.raises(AppError) as captured:
        await inventory_service().create_inventory_event(
            db_session,
            household_id=HOUSEHOLD_ID,
            user_id=USER_ID,
            data=InventoryEventCreate(
                item_id=item_id,
                event_type="stock_out",
                quantity=Decimal("3"),
                unit="개",
            ),
        )

    assert captured.value.code == "INSUFFICIENT_INVENTORY"
    snapshot_quantity = await db_session.scalar(
        select(Inventory.quantity).where(Inventory.item_id == item_id)
    )
    event_count = await db_session.scalar(
        select(func.count())
        .select_from(InventoryEvent)
        .where(InventoryEvent.item_id == item_id)
    )
    assert snapshot_quantity == Decimal("0")
    assert event_count == 0


async def test_cross_household_event_denied(
    db_session: AsyncSession,
    base: tuple[UUID, UUID],
) -> None:
    await seed_household(db_session, household_id=OTHER_HOUSEHOLD_ID, name="옆 집")
    item_id = await create_item(db_session, household_id=HOUSEHOLD_ID)

    with pytest.raises(AppError) as captured:
        await inventory_service().create_inventory_event(
            db_session,
            household_id=OTHER_HOUSEHOLD_ID,
            user_id=USER_ID,
            data=InventoryEventCreate(
                item_id=item_id,
                event_type="stock_in",
                quantity=Decimal("1"),
                unit="개",
            ),
        )

    assert captured.value.code == "HOUSEHOLD_ACCESS_DENIED"
    event_count = await db_session.scalar(
        select(func.count()).select_from(InventoryEvent)
    )
    assert event_count == 0


async def test_correction_then_rebuild_matches_ledger(
    db_session: AsyncSession,
    base: tuple[UUID, UUID],
) -> None:
    service = inventory_service()
    item_id = await create_item(db_session)
    created = await service.create_inventory_event(
        db_session,
        household_id=HOUSEHOLD_ID,
        user_id=USER_ID,
        data=InventoryEventCreate(
            item_id=item_id,
            event_type="stock_in",
            quantity=Decimal("20"),
            unit="개",
        ),
    )

    await service.correct_inventory_event(
        db_session,
        household_id=HOUSEHOLD_ID,
        user_id=USER_ID,
        event_id=created.event_id,
        data=InventoryEventCorrectionRequest(
            event_type="stock_in",
            quantity=Decimal("2"),
            unit="개",
        ),
    )

    snapshot_quantity = await db_session.scalar(
        select(Inventory.quantity).where(Inventory.item_id == item_id)
    )
    event_count = await db_session.scalar(
        select(func.count())
        .select_from(InventoryEvent)
        .where(InventoryEvent.item_id == item_id)
    )
    assert snapshot_quantity == Decimal("2")
    assert event_count == 3  # original + reversal + replacement

    # Drift the Snapshot away from the ledger, then rebuild from the events.
    # (The assertion reads above have autobegun a transaction on this session,
    # so mutate within it and commit rather than opening a nested one.)
    snapshot = await db_session.scalar(
        select(Inventory).where(Inventory.item_id == item_id)
    )
    assert snapshot is not None
    snapshot.quantity = Decimal("99")
    await db_session.commit()

    rebuild = await service.rebuild_inventory_snapshot(
        db_session,
        household_id=HOUSEHOLD_ID,
        item_id=item_id,
    )

    assert rebuild.changed is True
    assert rebuild.current_quantity == Decimal("2")
    repaired = await db_session.scalar(
        select(Inventory.quantity).where(Inventory.item_id == item_id)
    )
    assert repaired == Decimal("2")


async def test_for_update_serializes_concurrent_stock_out(
    integration_engine: AsyncEngine,
) -> None:
    session_factory = create_session_factory(integration_engine)
    async with session_factory() as setup_session:
        async with setup_session.begin():
            setup_session.add(Household(id=HOUSEHOLD_ID, name="우리 집"))
            setup_session.add(User(id=USER_ID, nickname="테스트 사용자"))
        item_id = await create_item(setup_session)
        await inventory_service().create_inventory_event(
            setup_session,
            household_id=HOUSEHOLD_ID,
            user_id=USER_ID,
            data=InventoryEventCreate(
                item_id=item_id,
                event_type="stock_in",
                quantity=Decimal("1"),
                unit="개",
            ),
        )

    async def consume() -> str:
        async with session_factory() as session:
            try:
                await inventory_service().create_inventory_event(
                    session,
                    household_id=HOUSEHOLD_ID,
                    user_id=USER_ID,
                    data=InventoryEventCreate(
                        item_id=item_id,
                        event_type="stock_out",
                        quantity=Decimal("1"),
                        unit="개",
                    ),
                )
                return "ok"
            except AppError as error:
                return error.code

    outcomes = sorted(await asyncio.gather(consume(), consume()))

    # The row lock serialises the two transactions: exactly one consumes the
    # unit, the other sees the updated Snapshot and is rejected. Without the
    # lock both could succeed and oversell to a negative quantity.
    assert outcomes == ["INSUFFICIENT_INVENTORY", "ok"]

    async with session_factory() as check_session:
        final_quantity = await check_session.scalar(
            select(Inventory.quantity).where(Inventory.item_id == item_id)
        )
        stock_out_count = await check_session.scalar(
            select(func.count())
            .select_from(InventoryEvent)
            .where(
                InventoryEvent.item_id == item_id,
                InventoryEvent.event_type == "stock_out",
            )
        )
    assert final_quantity == Decimal("0")
    assert stock_out_count == 1
