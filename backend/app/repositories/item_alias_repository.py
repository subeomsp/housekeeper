from collections import defaultdict
from typing import cast
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import ItemAlias


class ItemAliasRepository:
    async def list_for_household(
        self,
        session: AsyncSession,
        *,
        household_id: UUID,
    ) -> dict[UUID, list[ItemAlias]]:
        aliases = list(
            (
                await session.scalars(
                    select(ItemAlias)
                    .where(ItemAlias.household_id == household_id)
                    .order_by(ItemAlias.created_at.asc(), ItemAlias.id.asc())
                )
            ).all()
        )
        grouped: dict[UUID, list[ItemAlias]] = defaultdict(list)
        for alias in aliases:
            grouped[alias.inventory_item_id].append(alias)
        return dict(grouped)

    async def get_by_normalized_alias(
        self,
        session: AsyncSession,
        *,
        household_id: UUID,
        normalized_alias: str,
    ) -> ItemAlias | None:
        return cast(
            ItemAlias | None,
            await session.scalar(
                select(ItemAlias).where(
                    ItemAlias.household_id == household_id,
                    ItemAlias.normalized_alias == normalized_alias,
                )
            )
        )

    async def add(
        self,
        session: AsyncSession,
        *,
        alias: ItemAlias,
    ) -> None:
        session.add(alias)
        await session.flush()
        await session.refresh(alias)
