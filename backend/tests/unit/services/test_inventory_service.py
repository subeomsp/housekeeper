from datetime import UTC, datetime
from decimal import Decimal
from types import TracebackType
from typing import Any, cast
from uuid import UUID, uuid4

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import AppError
from app.models import AuditLog, Inventory, InventoryEvent, InventoryItem
from app.repositories.audit_log_repository import AuditLogRepository
from app.repositories.inventory_event_repository import (
    InventoryEventPage,
    InventoryEventRepository,
)
from app.repositories.inventory_repository import (
    CurrentInventoryPage,
    CurrentInventoryRecord,
    InventoryRepository,
    InventorySort,
    SortOrder,
)
from app.schemas.inventory import InventorySetQuantityRequest
from app.schemas.inventory_event import (
    InventoryEventCorrectionRequest,
    InventoryEventCreate,
)
from app.services.inventory_service import InventoryService

HOUSEHOLD_ID = UUID("00000000-0000-4000-8000-000000000099")
USER_ID = UUID("00000000-0000-4000-8000-000000000098")
ITEM_ID = UUID("00000000-0000-4000-8000-000000000100")
UPDATED_AT = datetime(2026, 7, 20, 10, 30, tzinfo=UTC)


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


class FakeInventoryRepository(InventoryRepository):
    def __init__(self) -> None:
        self.page = CurrentInventoryPage(records=[], total=0)
        self.detail: CurrentInventoryRecord | None = None
        self.locked: CurrentInventoryRecord | None = None
        self.list_arguments: dict[str, Any] = {}

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
        self.list_arguments = {
            "household_id": household_id,
            "search": search,
            "category": category,
            "include_zero": include_zero,
            "sort": sort,
            "order": order,
            "limit": limit,
            "offset": offset,
        }
        return self.page

    async def get_by_item_id(
        self,
        session: AsyncSession,
        *,
        item_id: UUID,
    ) -> CurrentInventoryRecord | None:
        return self.detail

    async def get_for_update_by_item_id(
        self,
        session: AsyncSession,
        *,
        item_id: UUID,
    ) -> CurrentInventoryRecord | None:
        return self.locked

    async def save_snapshot(
        self,
        session: AsyncSession,
        *,
        snapshot: Inventory,
    ) -> None:
        snapshot.updated_at = UPDATED_AT


class FakeInventoryEventRepository(InventoryEventRepository):
    def __init__(self) -> None:
        self.events: list[InventoryEvent] = []
        self.added_event: InventoryEvent | None = None
        self.added_events: list[InventoryEvent] = []
        self.locked_event: InventoryEvent | None = None
        self.requested_limit: int | None = None
        self.events_page = InventoryEventPage(records=[], total=0)
        self.list_events_arguments: dict[str, Any] = {}
        self.signed_total = Decimal("0")

    async def add(
        self,
        session: AsyncSession,
        *,
        event: InventoryEvent,
    ) -> None:
        event.created_at = UPDATED_AT
        self.added_event = event
        self.added_events.append(event)

    async def get_for_update_by_id(
        self,
        session: AsyncSession,
        *,
        event_id: UUID,
    ) -> InventoryEvent | None:
        return self.locked_event

    async def sum_signed_quantity(
        self,
        session: AsyncSession,
        *,
        household_id: UUID,
        item_id: UUID,
    ) -> Decimal:
        return self.signed_total

    async def list_recent_for_item(
        self,
        session: AsyncSession,
        *,
        household_id: UUID,
        item_id: UUID,
        limit: int,
    ) -> list[InventoryEvent]:
        self.requested_limit = limit
        return self.events

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
        self.list_events_arguments = {
            "household_id": household_id,
            "item_id": item_id,
            "event_type": event_type,
            "source": source,
            "created_from": created_from,
            "created_to": created_to,
            "limit": limit,
            "offset": offset,
        }
        return self.events_page


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
                "action": action,
                "target_id": target_id,
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
            created_at=UPDATED_AT,
        )


def make_record(*, household_id: UUID = HOUSEHOLD_ID) -> CurrentInventoryRecord:
    item = InventoryItem(
        id=ITEM_ID,
        household_id=household_id,
        name="우유",
        normalized_name="우유",
        default_unit="개",
        category="drink",
        is_active=True,
        created_at=UPDATED_AT,
        updated_at=UPDATED_AT,
    )
    snapshot = Inventory(
        id=UUID("00000000-0000-4000-8000-000000000101"),
        household_id=household_id,
        item_id=ITEM_ID,
        quantity=Decimal("2"),
        updated_at=UPDATED_AT,
    )
    return CurrentInventoryRecord(snapshot=snapshot, item=item)


def make_event() -> InventoryEvent:
    return InventoryEvent(
        id=UUID("00000000-0000-4000-8000-000000000102"),
        household_id=HOUSEHOLD_ID,
        item_id=ITEM_ID,
        event_type="stock_in",
        quantity=Decimal("2"),
        unit="개",
        signed_quantity=Decimal("2"),
        source="manual",
        created_at=UPDATED_AT,
    )


def make_stored_event(
    *,
    event_type: str = "stock_in",
    quantity: Decimal = Decimal("2"),
    signed_quantity: Decimal = Decimal("2"),
    household_id: UUID = HOUSEHOLD_ID,
    reversed_at: datetime | None = None,
) -> InventoryEvent:
    return InventoryEvent(
        id=UUID("00000000-0000-4000-8000-000000000110"),
        household_id=household_id,
        item_id=ITEM_ID,
        event_type=event_type,
        quantity=quantity,
        unit="개",
        signed_quantity=signed_quantity,
        source="manual",
        created_at=UPDATED_AT,
        reversed_at=reversed_at,
    )


async def test_list_current_inventory_uses_snapshot_and_normalizes_filters() -> None:
    repository = FakeInventoryRepository()
    repository.page = CurrentInventoryPage(records=[make_record()], total=1)
    service = InventoryService(repository, FakeInventoryEventRepository())

    result = await service.list_current_inventory(
        cast(AsyncSession, object()),
        household_id=HOUSEHOLD_ID,
        search=" 우 유 ",
        category=" drink ",
        include_zero=False,
        sort="quantity",
        order="asc",
        limit=20,
        offset=10,
    )

    assert result.total == 1
    assert result.items[0].quantity == Decimal("2")
    assert result.items[0].unit == "개"
    assert repository.list_arguments == {
        "household_id": HOUSEHOLD_ID,
        "search": "우유",
        "category": "drink",
        "include_zero": False,
        "sort": "quantity",
        "order": "asc",
        "limit": 20,
        "offset": 10,
    }


async def test_inventory_detail_combines_snapshot_and_recent_events() -> None:
    repository = FakeInventoryRepository()
    repository.detail = make_record()
    event_repository = FakeInventoryEventRepository()
    event_repository.events = [make_event()]
    service = InventoryService(repository, event_repository)

    result = await service.get_inventory_detail(
        cast(AsyncSession, object()),
        household_id=HOUSEHOLD_ID,
        item_id=ITEM_ID,
    )

    assert result.item.quantity == Decimal("2")
    assert result.recent_events[0].event_type == "stock_in"
    assert result.recent_events[0].signed_quantity == Decimal("2")
    assert event_repository.requested_limit == 10


async def test_inventory_detail_rejects_another_household() -> None:
    repository = FakeInventoryRepository()
    repository.detail = make_record(
        household_id=UUID("00000000-0000-4000-8000-000000000103")
    )
    event_repository = FakeInventoryEventRepository()
    service = InventoryService(repository, event_repository)

    with pytest.raises(AppError) as captured:
        await service.get_inventory_detail(
            cast(AsyncSession, object()),
            household_id=HOUSEHOLD_ID,
            item_id=ITEM_ID,
        )

    assert captured.value.code == "HOUSEHOLD_ACCESS_DENIED"
    assert event_repository.requested_limit is None


async def test_inventory_detail_returns_not_found() -> None:
    service = InventoryService(
        FakeInventoryRepository(),
        FakeInventoryEventRepository(),
    )

    with pytest.raises(AppError) as captured:
        await service.get_inventory_detail(
            cast(AsyncSession, object()),
            household_id=HOUSEHOLD_ID,
            item_id=ITEM_ID,
        )

    assert captured.value.code == "ITEM_NOT_FOUND"


async def test_stock_in_creates_positive_event_and_updates_snapshot() -> None:
    repository = FakeInventoryRepository()
    repository.locked = make_record()
    event_repository = FakeInventoryEventRepository()
    audit_repository = FakeAuditLogRepository()
    service = InventoryService(repository, event_repository, audit_repository)

    result = await service.create_inventory_event(
        cast(AsyncSession, FakeSession()),
        household_id=HOUSEHOLD_ID,
        user_id=USER_ID,
        data=InventoryEventCreate(
            item_id=ITEM_ID,
            event_type="stock_in",
            quantity=Decimal("3"),
            unit="개",
            note="장보기",
        ),
    )

    assert result.previous_quantity == Decimal("2")
    assert result.current_quantity == Decimal("5")
    assert result.signed_quantity == Decimal("3")
    assert repository.locked.snapshot.quantity == Decimal("5")
    assert event_repository.added_event is not None
    assert event_repository.added_event.created_by == USER_ID
    assert audit_repository.entries[0]["action"] == "inventory_event_created"


async def test_stock_out_creates_negative_event() -> None:
    repository = FakeInventoryRepository()
    repository.locked = make_record()
    event_repository = FakeInventoryEventRepository()
    service = InventoryService(
        repository,
        event_repository,
        FakeAuditLogRepository(),
    )

    result = await service.create_inventory_event(
        cast(AsyncSession, FakeSession()),
        household_id=HOUSEHOLD_ID,
        user_id=USER_ID,
        data=InventoryEventCreate(
            item_id=ITEM_ID,
            event_type="stock_out",
            quantity=Decimal("1"),
            unit="개",
        ),
    )

    assert result.signed_quantity == Decimal("-1")
    assert result.current_quantity == Decimal("1")


async def test_stock_out_rejects_negative_inventory_without_writes() -> None:
    repository = FakeInventoryRepository()
    repository.locked = make_record()
    event_repository = FakeInventoryEventRepository()
    audit_repository = FakeAuditLogRepository()
    service = InventoryService(repository, event_repository, audit_repository)

    with pytest.raises(AppError) as captured:
        await service.create_inventory_event(
            cast(AsyncSession, FakeSession()),
            household_id=HOUSEHOLD_ID,
            user_id=USER_ID,
            data=InventoryEventCreate(
                item_id=ITEM_ID,
                event_type="stock_out",
                quantity=Decimal("3"),
                unit="개",
            ),
        )

    assert captured.value.code == "INSUFFICIENT_INVENTORY"
    assert repository.locked.snapshot.quantity == Decimal("2")
    assert event_repository.added_event is None
    assert audit_repository.entries == []


async def test_inventory_event_rejects_unit_mismatch() -> None:
    repository = FakeInventoryRepository()
    repository.locked = make_record()
    service = InventoryService(
        repository,
        FakeInventoryEventRepository(),
        FakeAuditLogRepository(),
    )

    with pytest.raises(AppError) as captured:
        await service.create_inventory_event(
            cast(AsyncSession, FakeSession()),
            household_id=HOUSEHOLD_ID,
            user_id=USER_ID,
            data=InventoryEventCreate(
                item_id=ITEM_ID,
                event_type="stock_in",
                quantity=Decimal("1"),
                unit="병",
            ),
        )

    assert captured.value.code == "UNIT_MISMATCH"


async def test_inventory_event_rejects_inactive_item() -> None:
    repository = FakeInventoryRepository()
    repository.locked = make_record()
    repository.locked.item.is_active = False
    service = InventoryService(
        repository,
        FakeInventoryEventRepository(),
        FakeAuditLogRepository(),
    )

    with pytest.raises(AppError) as captured:
        await service.create_inventory_event(
            cast(AsyncSession, FakeSession()),
            household_id=HOUSEHOLD_ID,
            user_id=USER_ID,
            data=InventoryEventCreate(
                item_id=ITEM_ID,
                event_type="stock_in",
                quantity=Decimal("1"),
                unit="개",
            ),
        )

    assert captured.value.code == "INACTIVE_ITEM"


async def test_set_quantity_higher_target_creates_adjustment_in() -> None:
    repository = FakeInventoryRepository()
    repository.locked = make_record()
    event_repository = FakeInventoryEventRepository()
    audit_repository = FakeAuditLogRepository()
    service = InventoryService(repository, event_repository, audit_repository)

    result = await service.set_inventory_quantity(
        cast(AsyncSession, FakeSession()),
        household_id=HOUSEHOLD_ID,
        user_id=USER_ID,
        item_id=ITEM_ID,
        data=InventorySetQuantityRequest(
            quantity=Decimal("5"),
            unit="개",
            note="실제 수량 확인",
        ),
    )

    assert result.changed is True
    assert result.previous_quantity == Decimal("2")
    assert result.current_quantity == Decimal("5")
    assert result.event_id is not None
    assert repository.locked.snapshot.quantity == Decimal("5")
    added = event_repository.added_event
    assert added is not None
    assert added.event_type == "adjustment_in"
    assert added.quantity == Decimal("3")
    assert added.signed_quantity == Decimal("3")
    assert added.created_by == USER_ID
    assert audit_repository.entries[0]["action"] == "inventory_event_created"


async def test_set_quantity_lower_target_creates_adjustment_out() -> None:
    repository = FakeInventoryRepository()
    repository.locked = make_record()
    event_repository = FakeInventoryEventRepository()
    service = InventoryService(
        repository,
        event_repository,
        FakeAuditLogRepository(),
    )

    result = await service.set_inventory_quantity(
        cast(AsyncSession, FakeSession()),
        household_id=HOUSEHOLD_ID,
        user_id=USER_ID,
        item_id=ITEM_ID,
        data=InventorySetQuantityRequest(quantity=Decimal("0"), unit="개"),
    )

    assert result.changed is True
    assert result.current_quantity == Decimal("0")
    added = event_repository.added_event
    assert added is not None
    assert added.event_type == "adjustment_out"
    assert added.quantity == Decimal("2")
    assert added.signed_quantity == Decimal("-2")
    assert repository.locked.snapshot.quantity == Decimal("0")


async def test_set_quantity_equal_target_writes_nothing() -> None:
    repository = FakeInventoryRepository()
    repository.locked = make_record()
    event_repository = FakeInventoryEventRepository()
    audit_repository = FakeAuditLogRepository()
    service = InventoryService(repository, event_repository, audit_repository)

    result = await service.set_inventory_quantity(
        cast(AsyncSession, FakeSession()),
        household_id=HOUSEHOLD_ID,
        user_id=USER_ID,
        item_id=ITEM_ID,
        data=InventorySetQuantityRequest(quantity=Decimal("2"), unit="개"),
    )

    assert result.changed is False
    assert result.event_id is None
    assert result.created_at is None
    assert result.previous_quantity == Decimal("2")
    assert result.current_quantity == Decimal("2")
    assert repository.locked.snapshot.quantity == Decimal("2")
    assert event_repository.added_event is None
    assert audit_repository.entries == []


async def test_set_quantity_returns_not_found() -> None:
    service = InventoryService(
        FakeInventoryRepository(),
        FakeInventoryEventRepository(),
        FakeAuditLogRepository(),
    )

    with pytest.raises(AppError) as captured:
        await service.set_inventory_quantity(
            cast(AsyncSession, FakeSession()),
            household_id=HOUSEHOLD_ID,
            user_id=USER_ID,
            item_id=ITEM_ID,
            data=InventorySetQuantityRequest(quantity=Decimal("1"), unit="개"),
        )

    assert captured.value.code == "ITEM_NOT_FOUND"


async def test_set_quantity_rejects_another_household() -> None:
    repository = FakeInventoryRepository()
    repository.locked = make_record(
        household_id=UUID("00000000-0000-4000-8000-000000000103")
    )
    event_repository = FakeInventoryEventRepository()
    service = InventoryService(
        repository,
        event_repository,
        FakeAuditLogRepository(),
    )

    with pytest.raises(AppError) as captured:
        await service.set_inventory_quantity(
            cast(AsyncSession, FakeSession()),
            household_id=HOUSEHOLD_ID,
            user_id=USER_ID,
            item_id=ITEM_ID,
            data=InventorySetQuantityRequest(quantity=Decimal("1"), unit="개"),
        )

    assert captured.value.code == "HOUSEHOLD_ACCESS_DENIED"
    assert event_repository.added_event is None


async def test_set_quantity_rejects_inactive_item() -> None:
    repository = FakeInventoryRepository()
    repository.locked = make_record()
    repository.locked.item.is_active = False
    service = InventoryService(
        repository,
        FakeInventoryEventRepository(),
        FakeAuditLogRepository(),
    )

    with pytest.raises(AppError) as captured:
        await service.set_inventory_quantity(
            cast(AsyncSession, FakeSession()),
            household_id=HOUSEHOLD_ID,
            user_id=USER_ID,
            item_id=ITEM_ID,
            data=InventorySetQuantityRequest(quantity=Decimal("1"), unit="개"),
        )

    assert captured.value.code == "INACTIVE_ITEM"


async def test_set_quantity_rejects_unit_mismatch() -> None:
    repository = FakeInventoryRepository()
    repository.locked = make_record()
    service = InventoryService(
        repository,
        FakeInventoryEventRepository(),
        FakeAuditLogRepository(),
    )

    with pytest.raises(AppError) as captured:
        await service.set_inventory_quantity(
            cast(AsyncSession, FakeSession()),
            household_id=HOUSEHOLD_ID,
            user_id=USER_ID,
            item_id=ITEM_ID,
            data=InventorySetQuantityRequest(quantity=Decimal("1"), unit="병"),
        )

    assert captured.value.code == "UNIT_MISMATCH"


async def test_list_inventory_events_maps_records_and_forwards_filters() -> None:
    event_repository = FakeInventoryEventRepository()
    event_repository.events_page = InventoryEventPage(
        records=[make_event()],
        total=1,
    )
    service = InventoryService(
        FakeInventoryRepository(),
        event_repository,
        FakeAuditLogRepository(),
    )
    created_from = datetime(2026, 7, 1, tzinfo=UTC)
    created_to = datetime(2026, 7, 20, tzinfo=UTC)

    result = await service.list_inventory_events(
        cast(AsyncSession, object()),
        household_id=HOUSEHOLD_ID,
        item_id=ITEM_ID,
        event_type="stock_in",
        source="manual",
        created_from=created_from,
        created_to=created_to,
        limit=20,
        offset=5,
    )

    assert result.total == 1
    entry = result.items[0]
    assert entry.event_type == "stock_in"
    assert entry.source == "manual"
    assert entry.signed_quantity == Decimal("2")
    assert event_repository.list_events_arguments == {
        "household_id": HOUSEHOLD_ID,
        "item_id": ITEM_ID,
        "event_type": "stock_in",
        "source": "manual",
        "created_from": created_from,
        "created_to": created_to,
        "limit": 20,
        "offset": 5,
    }


async def test_correct_event_reverses_original_and_writes_replacement() -> None:
    repository = FakeInventoryRepository()
    repository.locked = make_record()
    event_repository = FakeInventoryEventRepository()
    event_repository.locked_event = make_stored_event()
    audit_repository = FakeAuditLogRepository()
    service = InventoryService(repository, event_repository, audit_repository)

    result = await service.correct_inventory_event(
        cast(AsyncSession, FakeSession()),
        household_id=HOUSEHOLD_ID,
        user_id=USER_ID,
        event_id=event_repository.locked_event.id,
        data=InventoryEventCorrectionRequest(
            event_type="stock_in",
            quantity=Decimal("5"),
            unit="개",
            note="2개가 아니라 5개",
        ),
    )

    assert result.previous_quantity == Decimal("2")
    assert result.current_quantity == Decimal("5")
    assert repository.locked.snapshot.quantity == Decimal("5")
    reversal, replacement = event_repository.added_events
    assert reversal.event_type == "event_reversal"
    assert reversal.signed_quantity == Decimal("-2")
    assert reversal.source == "correction"
    assert replacement.event_type == "stock_in"
    assert replacement.signed_quantity == Decimal("5")
    assert replacement.source == "correction"
    original = event_repository.locked_event
    assert original.reversed_at == UPDATED_AT
    assert original.reversed_by == USER_ID
    assert original.reversal_event_id == reversal.id
    assert result.reversal_event_id == reversal.id
    assert result.replacement_event_id == replacement.id
    assert audit_repository.entries[0]["action"] == "inventory_event_corrected"


async def test_cancel_event_creates_only_reversal() -> None:
    repository = FakeInventoryRepository()
    repository.locked = make_record()
    event_repository = FakeInventoryEventRepository()
    event_repository.locked_event = make_stored_event()
    audit_repository = FakeAuditLogRepository()
    service = InventoryService(repository, event_repository, audit_repository)

    result = await service.cancel_inventory_event(
        cast(AsyncSession, FakeSession()),
        household_id=HOUSEHOLD_ID,
        user_id=USER_ID,
        event_id=event_repository.locked_event.id,
    )

    assert result.previous_quantity == Decimal("2")
    assert result.current_quantity == Decimal("0")
    assert repository.locked.snapshot.quantity == Decimal("0")
    assert len(event_repository.added_events) == 1
    assert event_repository.added_events[0].event_type == "event_reversal"
    assert event_repository.locked_event.reversal_event_id == result.reversal_event_id
    assert audit_repository.entries[0]["action"] == "inventory_event_reversed"


async def test_cancel_event_rejects_negative_result_without_writes() -> None:
    repository = FakeInventoryRepository()
    repository.locked = make_record()
    event_repository = FakeInventoryEventRepository()
    event_repository.locked_event = make_stored_event(
        quantity=Decimal("5"),
        signed_quantity=Decimal("5"),
    )
    audit_repository = FakeAuditLogRepository()
    service = InventoryService(repository, event_repository, audit_repository)

    with pytest.raises(AppError) as captured:
        await service.cancel_inventory_event(
            cast(AsyncSession, FakeSession()),
            household_id=HOUSEHOLD_ID,
            user_id=USER_ID,
            event_id=event_repository.locked_event.id,
        )

    assert captured.value.code == "INSUFFICIENT_INVENTORY"
    assert repository.locked.snapshot.quantity == Decimal("2")
    assert event_repository.added_events == []
    assert audit_repository.entries == []


async def test_cancel_event_returns_not_found() -> None:
    service = InventoryService(
        FakeInventoryRepository(),
        FakeInventoryEventRepository(),
        FakeAuditLogRepository(),
    )

    with pytest.raises(AppError) as captured:
        await service.cancel_inventory_event(
            cast(AsyncSession, FakeSession()),
            household_id=HOUSEHOLD_ID,
            user_id=USER_ID,
            event_id=ITEM_ID,
        )

    assert captured.value.code == "EVENT_NOT_FOUND"


async def test_correct_event_rejects_already_reversed() -> None:
    repository = FakeInventoryRepository()
    repository.locked = make_record()
    event_repository = FakeInventoryEventRepository()
    event_repository.locked_event = make_stored_event(reversed_at=UPDATED_AT)
    service = InventoryService(
        repository,
        event_repository,
        FakeAuditLogRepository(),
    )

    with pytest.raises(AppError) as captured:
        await service.correct_inventory_event(
            cast(AsyncSession, FakeSession()),
            household_id=HOUSEHOLD_ID,
            user_id=USER_ID,
            event_id=event_repository.locked_event.id,
            data=InventoryEventCorrectionRequest(
                event_type="stock_in",
                quantity=Decimal("5"),
                unit="개",
            ),
        )

    assert captured.value.code == "EVENT_ALREADY_REVERSED"
    assert event_repository.added_events == []


async def test_cancel_event_rejects_reversal_event() -> None:
    repository = FakeInventoryRepository()
    repository.locked = make_record()
    event_repository = FakeInventoryEventRepository()
    event_repository.locked_event = make_stored_event(
        event_type="event_reversal",
        signed_quantity=Decimal("-2"),
    )
    service = InventoryService(
        repository,
        event_repository,
        FakeAuditLogRepository(),
    )

    with pytest.raises(AppError) as captured:
        await service.cancel_inventory_event(
            cast(AsyncSession, FakeSession()),
            household_id=HOUSEHOLD_ID,
            user_id=USER_ID,
            event_id=event_repository.locked_event.id,
        )

    assert captured.value.code == "EVENT_NOT_CORRECTABLE"


async def test_correct_event_rejects_unit_mismatch() -> None:
    repository = FakeInventoryRepository()
    repository.locked = make_record()
    event_repository = FakeInventoryEventRepository()
    event_repository.locked_event = make_stored_event()
    service = InventoryService(
        repository,
        event_repository,
        FakeAuditLogRepository(),
    )

    with pytest.raises(AppError) as captured:
        await service.correct_inventory_event(
            cast(AsyncSession, FakeSession()),
            household_id=HOUSEHOLD_ID,
            user_id=USER_ID,
            event_id=event_repository.locked_event.id,
            data=InventoryEventCorrectionRequest(
                event_type="stock_in",
                quantity=Decimal("5"),
                unit="병",
            ),
        )

    assert captured.value.code == "UNIT_MISMATCH"


async def test_cancel_event_rejects_another_household() -> None:
    repository = FakeInventoryRepository()
    repository.locked = make_record()
    event_repository = FakeInventoryEventRepository()
    event_repository.locked_event = make_stored_event(
        household_id=UUID("00000000-0000-4000-8000-000000000103"),
    )
    service = InventoryService(
        repository,
        event_repository,
        FakeAuditLogRepository(),
    )

    with pytest.raises(AppError) as captured:
        await service.cancel_inventory_event(
            cast(AsyncSession, FakeSession()),
            household_id=HOUSEHOLD_ID,
            user_id=USER_ID,
            event_id=event_repository.locked_event.id,
        )

    assert captured.value.code == "HOUSEHOLD_ACCESS_DENIED"
    assert event_repository.added_events == []


async def test_rebuild_snapshot_repairs_drift_from_event_sum() -> None:
    repository = FakeInventoryRepository()
    record = make_record()
    record.snapshot.quantity = Decimal("99")
    repository.locked = record
    event_repository = FakeInventoryEventRepository()
    event_repository.signed_total = Decimal("3")
    service = InventoryService(
        repository,
        event_repository,
        FakeAuditLogRepository(),
    )

    result = await service.rebuild_inventory_snapshot(
        cast(AsyncSession, FakeSession()),
        household_id=HOUSEHOLD_ID,
        item_id=ITEM_ID,
    )

    assert result.changed is True
    assert result.previous_quantity == Decimal("99")
    assert result.current_quantity == Decimal("3")
    assert repository.locked.snapshot.quantity == Decimal("3")


async def test_rebuild_snapshot_no_change_when_already_consistent() -> None:
    repository = FakeInventoryRepository()
    repository.locked = make_record()
    event_repository = FakeInventoryEventRepository()
    event_repository.signed_total = Decimal("2")
    service = InventoryService(
        repository,
        event_repository,
        FakeAuditLogRepository(),
    )

    result = await service.rebuild_inventory_snapshot(
        cast(AsyncSession, FakeSession()),
        household_id=HOUSEHOLD_ID,
        item_id=ITEM_ID,
    )

    assert result.changed is False
    assert result.current_quantity == Decimal("2")
    assert repository.locked.snapshot.quantity == Decimal("2")


async def test_rebuild_snapshot_returns_not_found() -> None:
    service = InventoryService(
        FakeInventoryRepository(),
        FakeInventoryEventRepository(),
        FakeAuditLogRepository(),
    )

    with pytest.raises(AppError) as captured:
        await service.rebuild_inventory_snapshot(
            cast(AsyncSession, FakeSession()),
            household_id=HOUSEHOLD_ID,
            item_id=ITEM_ID,
        )

    assert captured.value.code == "ITEM_NOT_FOUND"


async def test_rebuild_snapshot_rejects_another_household() -> None:
    repository = FakeInventoryRepository()
    repository.locked = make_record(
        household_id=UUID("00000000-0000-4000-8000-000000000103")
    )
    service = InventoryService(
        repository,
        FakeInventoryEventRepository(),
        FakeAuditLogRepository(),
    )

    with pytest.raises(AppError) as captured:
        await service.rebuild_inventory_snapshot(
            cast(AsyncSession, FakeSession()),
            household_id=HOUSEHOLD_ID,
            item_id=ITEM_ID,
        )

    assert captured.value.code == "HOUSEHOLD_ACCESS_DENIED"

