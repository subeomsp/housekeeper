from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from uuid import UUID

from sqlalchemy import ColumnElement, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import InventoryEvent


@dataclass(frozen=True)
class InventoryEventPage:
    records: list[InventoryEvent]
    total: int


class InventoryEventRepository:
    async def add(
        self,
        session: AsyncSession,
        *,
        event: InventoryEvent,
    ) -> None:
        session.add(event)
        await session.flush()
        await session.refresh(event)

    async def sum_signed_quantity(
        self,
        session: AsyncSession,
        *,
        household_id: UUID,
        item_id: UUID,
    ) -> Decimal:
        total = await session.scalar(
            select(func.coalesce(func.sum(InventoryEvent.signed_quantity), 0)).where(
                InventoryEvent.household_id == household_id,
                InventoryEvent.item_id == item_id,
            )
        )
        return Decimal(total) if total is not None else Decimal("0")

    async def get_for_update_by_id(
        self,
        session: AsyncSession,
        *,
        event_id: UUID,
    ) -> InventoryEvent | None:
        events = await session.scalars(
            select(InventoryEvent)
            .where(InventoryEvent.id == event_id)
            .with_for_update()
        )
        return events.one_or_none()

    async def list_recent_for_item(
        self,
        session: AsyncSession,
        *,
        household_id: UUID,
        item_id: UUID,
        limit: int,
    ) -> list[InventoryEvent]:
        events = await session.scalars(
            select(InventoryEvent)
            .where(
                InventoryEvent.household_id == household_id,
                InventoryEvent.item_id == item_id,
            )
            .order_by(
                InventoryEvent.created_at.desc(),
                InventoryEvent.id.desc(),
            )
            .limit(limit)
        )
        return list(events.all())

    async def list_events(
        self,
        session: AsyncSession,
        *,
        household_id: UUID,
        item_id: UUID | None,
        event_type: str | None,
        source: str | None,
        created_from: datetime | None,
        created_to: datetime | None,
        limit: int,
        offset: int,
    ) -> InventoryEventPage:
        filters: list[ColumnElement[bool]] = [
            InventoryEvent.household_id == household_id,
        ]
        if item_id is not None:
            filters.append(InventoryEvent.item_id == item_id)
        if event_type is not None:
            filters.append(InventoryEvent.event_type == event_type)
        if source is not None:
            filters.append(InventoryEvent.source == source)
        if created_from is not None:
            filters.append(InventoryEvent.created_at >= created_from)
        if created_to is not None:
            filters.append(InventoryEvent.created_at <= created_to)

        total = await session.scalar(
            select(func.count(InventoryEvent.id)).where(*filters)
        )
        events = await session.scalars(
            select(InventoryEvent)
            .where(*filters)
            .order_by(
                InventoryEvent.created_at.desc(),
                InventoryEvent.id.desc(),
            )
            .limit(limit)
            .offset(offset)
        )
        return InventoryEventPage(records=list(events.all()), total=total or 0)
