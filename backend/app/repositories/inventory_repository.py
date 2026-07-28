from dataclasses import dataclass
from decimal import Decimal
from typing import Literal
from uuid import UUID

from sqlalchemy import Select, asc, desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Inventory, InventoryItem

InventorySort = Literal["updated_at", "name", "quantity"]
SortOrder = Literal["asc", "desc"]


@dataclass(frozen=True)
class CurrentInventoryRecord:
    snapshot: Inventory
    item: InventoryItem


@dataclass(frozen=True)
class CurrentInventoryPage:
    records: list[CurrentInventoryRecord]
    total: int


class InventoryRepository:
    async def list_current(
        self,
        session: AsyncSession,
        *,
        household_id: UUID,
        search: str | None,
        category: str | None,
        include_zero: bool,
        sort: InventorySort,
        order: SortOrder,
        limit: int,
        offset: int,
    ) -> CurrentInventoryPage:
        filters = [
            Inventory.household_id == household_id,
            InventoryItem.household_id == household_id,
            InventoryItem.is_active.is_(True),
        ]
        if search:
            filters.append(InventoryItem.normalized_name.contains(search))
        if category:
            filters.append(InventoryItem.category == category)
        if not include_zero:
            filters.append(Inventory.quantity > Decimal("0"))

        total = await session.scalar(
            select(func.count(Inventory.id))
            .join(InventoryItem, InventoryItem.id == Inventory.item_id)
            .where(*filters)
        )
        query = (
            select(Inventory, InventoryItem)
            .join(InventoryItem, InventoryItem.id == Inventory.item_id)
            .where(*filters)
        )
        query = self._apply_order(query, sort=sort, order=order)
        rows = (await session.execute(query.limit(limit).offset(offset))).all()

        return CurrentInventoryPage(
            records=[
                CurrentInventoryRecord(snapshot=row[0], item=row[1]) for row in rows
            ],
            total=total or 0,
        )

    async def get_by_item_id(
        self,
        session: AsyncSession,
        *,
        item_id: UUID,
    ) -> CurrentInventoryRecord | None:
        row = (
            await session.execute(
                select(Inventory, InventoryItem)
                .join(InventoryItem, InventoryItem.id == Inventory.item_id)
                .where(Inventory.item_id == item_id)
            )
        ).one_or_none()
        if row is None:
            return None
        return CurrentInventoryRecord(snapshot=row[0], item=row[1])

    async def get_for_update_by_item_id(
        self,
        session: AsyncSession,
        *,
        item_id: UUID,
    ) -> CurrentInventoryRecord | None:
        row = (
            await session.execute(
                select(Inventory, InventoryItem)
                .join(InventoryItem, InventoryItem.id == Inventory.item_id)
                .where(Inventory.item_id == item_id)
                .with_for_update()
            )
        ).one_or_none()
        if row is None:
            return None
        return CurrentInventoryRecord(snapshot=row[0], item=row[1])

    async def get_many_for_update(
        self,
        session: AsyncSession,
        *,
        item_ids: list[UUID],
    ) -> list[CurrentInventoryRecord]:
        if not item_ids:
            return []
        rows = (
            await session.execute(
                select(Inventory, InventoryItem)
                .join(InventoryItem, InventoryItem.id == Inventory.item_id)
                .where(Inventory.item_id.in_(item_ids))
                .order_by(Inventory.item_id.asc())
                .with_for_update(of=Inventory)
            )
        ).all()
        return [
            CurrentInventoryRecord(snapshot=row[0], item=row[1]) for row in rows
        ]

    async def save_snapshot(
        self,
        session: AsyncSession,
        *,
        snapshot: Inventory,
    ) -> None:
        await session.flush()
        await session.refresh(snapshot)

    @staticmethod
    def _apply_order(
        query: Select[tuple[Inventory, InventoryItem]],
        *,
        sort: InventorySort,
        order: SortOrder,
    ) -> Select[tuple[Inventory, InventoryItem]]:
        sort_columns = {
            "updated_at": Inventory.updated_at,
            "name": InventoryItem.name,
            "quantity": Inventory.quantity,
        }
        direction = asc if order == "asc" else desc
        return query.order_by(direction(sort_columns[sort]), Inventory.item_id.asc())
