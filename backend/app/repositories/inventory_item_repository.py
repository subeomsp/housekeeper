from dataclasses import dataclass
from decimal import Decimal
from typing import cast
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Inventory, InventoryItem


@dataclass(frozen=True)
class InventoryItemRecord:
    item: InventoryItem
    current_quantity: Decimal


@dataclass(frozen=True)
class InventoryItemPage:
    records: list[InventoryItemRecord]
    total: int


@dataclass(frozen=True)
class PlannerInventoryRecord:
    item: InventoryItem
    current_quantity: Decimal


class InventoryItemRepository:
    async def list_active_for_planner(
        self,
        session: AsyncSession,
        *,
        household_id: UUID,
    ) -> list[PlannerInventoryRecord]:
        rows = (
            await session.execute(
                select(InventoryItem, Inventory.quantity)
                .join(
                    Inventory,
                    (Inventory.household_id == InventoryItem.household_id)
                    & (Inventory.item_id == InventoryItem.id),
                )
                .where(
                    InventoryItem.household_id == household_id,
                    InventoryItem.is_active.is_(True),
                )
                .order_by(InventoryItem.name.asc(), InventoryItem.id.asc())
            )
        ).all()
        return [
            PlannerInventoryRecord(item=row[0], current_quantity=row[1])
            for row in rows
        ]

    async def normalized_name_exists(
        self,
        session: AsyncSession,
        *,
        household_id: UUID,
        normalized_name: str,
        exclude_item_id: UUID | None = None,
    ) -> bool:
        query = select(InventoryItem.id).where(
            InventoryItem.household_id == household_id,
            InventoryItem.normalized_name == normalized_name,
        )
        if exclude_item_id is not None:
            query = query.where(InventoryItem.id != exclude_item_id)
        item_id = await session.scalar(query.limit(1))
        return item_id is not None

    async def get_by_normalized_name(
        self,
        session: AsyncSession,
        *,
        household_id: UUID,
        normalized_name: str,
    ) -> InventoryItem | None:
        return cast(
            InventoryItem | None,
            await session.scalar(
                select(InventoryItem).where(
                    InventoryItem.household_id == household_id,
                    InventoryItem.normalized_name == normalized_name,
                )
            )
        )

    async def add_with_snapshot(
        self,
        session: AsyncSession,
        *,
        item: InventoryItem,
        snapshot: Inventory,
    ) -> None:
        # Insert the item first so the row exists before the snapshot's
        # foreign key references it; a single combined flush is not guaranteed
        # to order the two inserts and fails the FK on real PostgreSQL.
        session.add(item)
        await session.flush()
        session.add(snapshot)
        await session.flush()
        await session.refresh(item)

    async def get_with_quantity_for_update(
        self,
        session: AsyncSession,
        *,
        item_id: UUID,
    ) -> InventoryItemRecord | None:
        row = (
            await session.execute(
                select(InventoryItem, Inventory.quantity)
                .join(
                    Inventory,
                    (Inventory.household_id == InventoryItem.household_id)
                    & (Inventory.item_id == InventoryItem.id),
                )
                .where(InventoryItem.id == item_id)
                .with_for_update()
            )
        ).one_or_none()
        if row is None:
            return None
        return InventoryItemRecord(item=row[0], current_quantity=row[1])

    async def save(self, session: AsyncSession, *, item: InventoryItem) -> None:
        await session.flush()
        await session.refresh(item)

    async def list_with_quantity(
        self,
        session: AsyncSession,
        *,
        household_id: UUID,
        search: str | None,
        category: str | None,
        include_inactive: bool,
        limit: int,
        offset: int,
    ) -> InventoryItemPage:
        filters = [InventoryItem.household_id == household_id]
        if search:
            filters.append(InventoryItem.normalized_name.contains(search))
        if category:
            filters.append(InventoryItem.category == category)
        if not include_inactive:
            filters.append(InventoryItem.is_active.is_(True))

        total = await session.scalar(
            select(func.count(InventoryItem.id)).where(*filters)
        )
        rows = (
            await session.execute(
                select(InventoryItem, Inventory.quantity)
                .join(
                    Inventory,
                    (Inventory.household_id == InventoryItem.household_id)
                    & (Inventory.item_id == InventoryItem.id),
                )
                .where(*filters)
                .order_by(InventoryItem.name.asc(), InventoryItem.id.asc())
                .limit(limit)
                .offset(offset)
            )
        ).all()

        return InventoryItemPage(
            records=[
                InventoryItemRecord(item=row[0], current_quantity=row[1])
                for row in rows
            ],
            total=total or 0,
        )
