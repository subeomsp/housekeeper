from datetime import UTC, datetime
from decimal import Decimal
from types import TracebackType
from typing import Any, cast
from uuid import UUID, uuid4

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import AppError
from app.models import AuditLog, Inventory, InventoryItem
from app.repositories.audit_log_repository import AuditLogRepository
from app.repositories.inventory_item_repository import (
    InventoryItemPage,
    InventoryItemRecord,
    InventoryItemRepository,
)
from app.schemas.inventory_item import InventoryItemCreate, InventoryItemUpdate
from app.services.inventory_item_service import InventoryItemService

HOUSEHOLD_ID = UUID("00000000-0000-4000-8000-000000000099")
USER_ID = UUID("00000000-0000-4000-8000-000000000098")
CREATED_AT = datetime(2026, 7, 20, tzinfo=UTC)


class FakeTransaction:
    async def __aenter__(self) -> None:
        return None

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_value: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        return None


class FakeSession:
    def begin(self) -> FakeTransaction:
        return FakeTransaction()


class FakeInventoryItemRepository(InventoryItemRepository):
    def __init__(self, *, duplicate: bool = False) -> None:
        self.duplicate = duplicate
        self.added_item: InventoryItem | None = None
        self.added_snapshot: Inventory | None = None
        self.page = InventoryItemPage(records=[], total=0)
        self.locked_record: InventoryItemRecord | None = None

    async def normalized_name_exists(
        self,
        session: AsyncSession,
        *,
        household_id: UUID,
        normalized_name: str,
        exclude_item_id: UUID | None = None,
    ) -> bool:
        return self.duplicate

    async def add_with_snapshot(
        self,
        session: AsyncSession,
        *,
        item: InventoryItem,
        snapshot: Inventory,
    ) -> None:
        item.created_at = CREATED_AT
        self.added_item = item
        self.added_snapshot = snapshot

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
        return self.page

    async def get_with_quantity_for_update(
        self,
        session: AsyncSession,
        *,
        item_id: UUID,
    ) -> InventoryItemRecord | None:
        return self.locked_record

    async def save(self, session: AsyncSession, *, item: InventoryItem) -> None:
        item.updated_at = CREATED_AT


class FakeAuditLogRepository(AuditLogRepository):
    def __init__(self) -> None:
        self.entries: list[dict[str, Any]] = []

    async def add(
        self,
        session: AsyncSession,
        *,
        household_id: UUID,
        user_id: UUID | None,
        action: str,
        target_type: str,
        target_id: UUID,
        before_json: dict[str, Any] | None,
        after_json: dict[str, Any] | None,
    ) -> AuditLog:
        self.entries.append(
            {
                "household_id": household_id,
                "user_id": user_id,
                "action": action,
                "target_type": target_type,
                "target_id": target_id,
                "before_json": before_json,
                "after_json": after_json,
            }
        )
        return AuditLog(
            id=uuid4(),
            household_id=household_id,
            user_id=user_id,
            action=action,
            target_type=target_type,
            target_id=target_id,
            before_json=before_json,
            after_json=after_json,
            created_at=CREATED_AT,
        )


def make_service(
    repository: FakeInventoryItemRepository,
) -> tuple[InventoryItemService, FakeAuditLogRepository]:
    audit_repository = FakeAuditLogRepository()
    return InventoryItemService(repository, audit_repository), audit_repository


def make_item(*, household_id: UUID = HOUSEHOLD_ID) -> InventoryItem:
    return InventoryItem(
        id=UUID("00000000-0000-4000-8000-000000000100"),
        household_id=household_id,
        name="우유",
        normalized_name="우유",
        default_unit="개",
        category="drink",
        is_active=True,
        created_at=CREATED_AT,
        updated_at=CREATED_AT,
    )


async def test_create_item_builds_item_and_zero_snapshot_in_one_transaction() -> None:
    repository = FakeInventoryItemRepository()
    service, audit_repository = make_service(repository)
    session = cast(AsyncSession, FakeSession())

    result = await service.create_item(
        session,
        household_id=HOUSEHOLD_ID,
        user_id=USER_ID,
        data=InventoryItemCreate(
            name=" 코카콜라 제로 ",
            default_unit="캔",
            category="drink",
        ),
    )

    assert repository.added_item is not None
    assert repository.added_item.normalized_name == "코카콜라제로"
    assert repository.added_snapshot is not None
    assert repository.added_snapshot.item_id == repository.added_item.id
    assert repository.added_snapshot.quantity == Decimal("0")
    assert result.current_quantity == Decimal("0")
    assert audit_repository.entries[0]["action"] == "inventory_item_created"
    assert audit_repository.entries[0]["before_json"] is None


async def test_create_item_rejects_duplicate_normalized_name() -> None:
    repository = FakeInventoryItemRepository(duplicate=True)
    service, audit_repository = make_service(repository)
    session = cast(AsyncSession, FakeSession())

    with pytest.raises(AppError) as captured:
        await service.create_item(
            session,
            household_id=HOUSEHOLD_ID,
            user_id=USER_ID,
            data=InventoryItemCreate(name="우 유", default_unit="개"),
        )

    assert captured.value.code == "DUPLICATE_ITEM_NAME"
    assert captured.value.status_code == 409
    assert repository.added_item is None
    assert audit_repository.entries == []


async def test_list_items_flattens_snapshot_quantity() -> None:
    repository = FakeInventoryItemRepository()
    item = make_item()
    repository.page = InventoryItemPage(
        records=[InventoryItemRecord(item=item, current_quantity=Decimal("2"))],
        total=1,
    )
    service, _audit_repository = make_service(repository)

    result = await service.list_items(
        cast(AsyncSession, FakeSession()),
        household_id=HOUSEHOLD_ID,
        search=None,
        category=None,
        include_inactive=False,
        limit=50,
        offset=0,
    )

    assert result.total == 1
    assert result.items[0].name == "우유"
    assert result.items[0].current_quantity == Decimal("2")


async def test_update_item_changes_name_category_and_normalized_name() -> None:
    repository = FakeInventoryItemRepository()
    item = make_item()
    repository.locked_record = InventoryItemRecord(
        item=item,
        current_quantity=Decimal("0"),
    )
    service, audit_repository = make_service(repository)

    result = await service.update_item(
        cast(AsyncSession, FakeSession()),
        household_id=HOUSEHOLD_ID,
        user_id=USER_ID,
        item_id=item.id,
        data=InventoryItemUpdate(name=" 저지방 우유 ", category=None),
    )

    assert result.name == "저지방 우유"
    assert item.normalized_name == "저지방우유"
    assert item.category is None
    assert audit_repository.entries[0]["action"] == "inventory_item_updated"
    assert audit_repository.entries[0]["before_json"]["name"] == "우유"
    assert audit_repository.entries[0]["after_json"]["name"] == "저지방 우유"


async def test_update_item_blocks_unit_change_when_quantity_remains() -> None:
    repository = FakeInventoryItemRepository()
    item = make_item()
    repository.locked_record = InventoryItemRecord(
        item=item,
        current_quantity=Decimal("2"),
    )
    service, audit_repository = make_service(repository)

    with pytest.raises(AppError) as captured:
        await service.update_item(
            cast(AsyncSession, FakeSession()),
            household_id=HOUSEHOLD_ID,
            user_id=USER_ID,
            item_id=item.id,
            data=InventoryItemUpdate(default_unit="병"),
        )

    assert captured.value.code == "UNIT_CHANGE_REQUIRES_ZERO_INVENTORY"
    assert item.default_unit == "개"
    assert audit_repository.entries == []


async def test_archive_item_blocks_item_with_inventory() -> None:
    repository = FakeInventoryItemRepository()
    item = make_item()
    repository.locked_record = InventoryItemRecord(
        item=item,
        current_quantity=Decimal("1"),
    )
    service, audit_repository = make_service(repository)

    with pytest.raises(AppError) as captured:
        await service.archive_item(
            cast(AsyncSession, FakeSession()),
            household_id=HOUSEHOLD_ID,
            user_id=USER_ID,
            item_id=item.id,
        )

    assert captured.value.code == "ITEM_HAS_INVENTORY"
    assert item.is_active is True
    assert audit_repository.entries == []


async def test_archive_and_restore_item_preserve_record() -> None:
    repository = FakeInventoryItemRepository()
    item = make_item()
    repository.locked_record = InventoryItemRecord(
        item=item,
        current_quantity=Decimal("0"),
    )
    service, audit_repository = make_service(repository)
    session = cast(AsyncSession, FakeSession())

    archived = await service.archive_item(
        session,
        household_id=HOUSEHOLD_ID,
        user_id=USER_ID,
        item_id=item.id,
    )
    restored = await service.restore_item(
        session,
        household_id=HOUSEHOLD_ID,
        user_id=USER_ID,
        item_id=item.id,
    )

    assert archived.is_active is False
    assert restored.is_active is True
    assert restored.id == archived.id
    assert [entry["action"] for entry in audit_repository.entries] == [
        "inventory_item_archived",
        "inventory_item_restored",
    ]


async def test_update_item_rejects_another_household() -> None:
    repository = FakeInventoryItemRepository()
    other_household_id = UUID("00000000-0000-4000-8000-000000000101")
    item = make_item(household_id=other_household_id)
    repository.locked_record = InventoryItemRecord(
        item=item,
        current_quantity=Decimal("0"),
    )
    service, audit_repository = make_service(repository)

    with pytest.raises(AppError) as captured:
        await service.update_item(
            cast(AsyncSession, FakeSession()),
            household_id=HOUSEHOLD_ID,
            user_id=USER_ID,
            item_id=item.id,
            data=InventoryItemUpdate(name="새 이름"),
        )

    assert captured.value.code == "HOUSEHOLD_ACCESS_DENIED"
    assert audit_repository.entries == []
