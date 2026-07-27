import asyncio
from dataclasses import dataclass
from decimal import Decimal
from uuid import UUID, uuid5

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.core.database import async_session_factory
from app.core.defaults import (
    DEFAULT_HOUSEHOLD_ID,
    DEFAULT_HOUSEHOLD_MEMBER_ID,
    DEFAULT_HOUSEHOLD_NAME,
    DEFAULT_USER_ID,
    DEFAULT_USER_NICKNAME,
)
from app.models import Household, HouseholdMember, Inventory, InventoryItem, User
from app.services.inventory_item_service import normalize_item_name

SEED_NAMESPACE = UUID("00000000-0000-4000-8000-000000000010")
SEED_ITEMS = (
    ("우유", "개", "drink"),
    ("계란", "개", "food"),
    ("제로콜라", "캔", "drink"),
    ("맥주", "캔", "drink"),
    ("참치캔", "개", "food"),
)


@dataclass(frozen=True)
class SeedSummary:
    households_created: int = 0
    users_created: int = 0
    memberships_created: int = 0
    items_created: int = 0
    snapshots_created: int = 0


async def seed_database(
    session_factory: async_sessionmaker[AsyncSession] = async_session_factory,
) -> SeedSummary:
    counters = {
        "households_created": 0,
        "users_created": 0,
        "memberships_created": 0,
        "items_created": 0,
        "snapshots_created": 0,
    }

    async with session_factory() as session, session.begin():
        household = await session.get(Household, DEFAULT_HOUSEHOLD_ID)
        if household is None:
            household = Household(
                id=DEFAULT_HOUSEHOLD_ID,
                name=DEFAULT_HOUSEHOLD_NAME,
            )
            session.add(household)
            counters["households_created"] += 1

        user = await session.get(User, DEFAULT_USER_ID)
        if user is None:
            user = User(
                id=DEFAULT_USER_ID,
                nickname=DEFAULT_USER_NICKNAME,
            )
            session.add(user)
            counters["users_created"] += 1

        # Flush the parent rows (household, user) before inserting rows that
        # reference them. The models use explicit FKs without relationships, so
        # the ORM does not order these cross-table inserts on its own.
        await session.flush()

        membership = await session.scalar(
            select(HouseholdMember).where(
                HouseholdMember.household_id == DEFAULT_HOUSEHOLD_ID,
                HouseholdMember.user_id == DEFAULT_USER_ID,
            )
        )
        if membership is None:
            session.add(
                HouseholdMember(
                    id=DEFAULT_HOUSEHOLD_MEMBER_ID,
                    household_id=DEFAULT_HOUSEHOLD_ID,
                    user_id=DEFAULT_USER_ID,
                    role="owner",
                )
            )
            counters["memberships_created"] += 1

        for name, default_unit, category in SEED_ITEMS:
            normalized_name = normalize_item_name(name)
            item = await session.scalar(
                select(InventoryItem).where(
                    InventoryItem.household_id == DEFAULT_HOUSEHOLD_ID,
                    InventoryItem.normalized_name == normalized_name,
                )
            )
            if item is None:
                item = InventoryItem(
                    id=uuid5(SEED_NAMESPACE, f"item:{normalized_name}"),
                    household_id=DEFAULT_HOUSEHOLD_ID,
                    name=name,
                    normalized_name=normalized_name,
                    default_unit=default_unit,
                    category=category,
                )
                session.add(item)
                await session.flush()  # item row must exist before its snapshot FK
                counters["items_created"] += 1

            snapshot = await session.scalar(
                select(Inventory).where(
                    Inventory.household_id == DEFAULT_HOUSEHOLD_ID,
                    Inventory.item_id == item.id,
                )
            )
            if snapshot is None:
                session.add(
                    Inventory(
                        id=uuid5(SEED_NAMESPACE, f"snapshot:{item.id}"),
                        household_id=DEFAULT_HOUSEHOLD_ID,
                        item_id=item.id,
                        quantity=Decimal("0"),
                    )
                )
                counters["snapshots_created"] += 1

    return SeedSummary(**counters)


async def main() -> None:
    summary = await seed_database()
    print(
        "Seed complete: "
        f"households={summary.households_created}, "
        f"users={summary.users_created}, "
        f"memberships={summary.memberships_created}, "
        f"items={summary.items_created}, "
        f"snapshots={summary.snapshots_created}"
    )


if __name__ == "__main__":
    asyncio.run(main())

