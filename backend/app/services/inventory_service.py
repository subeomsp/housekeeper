from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from typing import Any
from uuid import UUID, uuid4

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import (
    event_already_reversed_error,
    event_not_correctable_error,
    event_not_found_error,
    household_access_denied_error,
    inactive_item_error,
    insufficient_inventory_error,
    item_not_found_error,
    unit_mismatch_error,
)
from app.models import InventoryEvent
from app.repositories.audit_log_repository import AuditLogRepository
from app.repositories.inventory_event_repository import InventoryEventRepository
from app.repositories.inventory_repository import (
    CurrentInventoryRecord,
    InventoryRepository,
)
from app.schemas.inventory import (
    InventorySetQuantityRequest,
    InventorySort,
    SortOrder,
)
from app.schemas.inventory_event import (
    InventoryEventCorrectionRequest,
    InventoryEventCreate,
    InventoryEventType,
)
from app.services.inventory_item_service import normalize_item_name


@dataclass(frozen=True)
class CurrentInventoryView:
    item_id: UUID
    name: str
    quantity: Decimal
    unit: str
    category: str | None
    is_active: bool
    updated_at: datetime


@dataclass(frozen=True)
class CurrentInventoryListView:
    items: list[CurrentInventoryView]
    total: int


@dataclass(frozen=True)
class RecentInventoryEventView:
    id: UUID
    event_type: str
    quantity: Decimal
    signed_quantity: Decimal
    unit: str
    created_at: datetime


@dataclass(frozen=True)
class InventoryDetailView:
    item: CurrentInventoryView
    recent_events: list[RecentInventoryEventView]


@dataclass(frozen=True)
class InventoryEventCreateView:
    event_id: UUID
    item_id: UUID
    event_type: InventoryEventType
    quantity: Decimal
    signed_quantity: Decimal
    previous_quantity: Decimal
    current_quantity: Decimal
    created_at: datetime


@dataclass(frozen=True)
class InventorySetQuantityView:
    event_id: UUID | None
    item_id: UUID
    previous_quantity: Decimal
    current_quantity: Decimal
    changed: bool
    created_at: datetime | None


@dataclass(frozen=True)
class InventoryEventListEntryView:
    id: UUID
    item_id: UUID
    event_type: str
    quantity: Decimal
    signed_quantity: Decimal
    unit: str
    source: str
    note: str | None
    created_by: UUID | None
    created_at: datetime


@dataclass(frozen=True)
class InventoryEventListView:
    items: list[InventoryEventListEntryView]
    total: int


@dataclass(frozen=True)
class InventoryEventCorrectionView:
    original_event_id: UUID
    reversal_event_id: UUID
    replacement_event_id: UUID
    previous_quantity: Decimal
    current_quantity: Decimal
    corrected_at: datetime


@dataclass(frozen=True)
class InventoryEventCancellationView:
    original_event_id: UUID
    reversal_event_id: UUID
    previous_quantity: Decimal
    current_quantity: Decimal
    cancelled_at: datetime


@dataclass(frozen=True)
class InventorySnapshotRebuildView:
    item_id: UUID
    previous_quantity: Decimal
    current_quantity: Decimal
    changed: bool


class InventoryService:
    def __init__(
        self,
        repository: InventoryRepository,
        event_repository: InventoryEventRepository,
        audit_log_repository: AuditLogRepository | None = None,
    ) -> None:
        self.repository = repository
        self.event_repository = event_repository
        self.audit_log_repository = audit_log_repository or AuditLogRepository()

    async def list_current_inventory(
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
    ) -> CurrentInventoryListView:
        normalized_search = normalize_item_name(search) if search else None
        normalized_category = category.strip() if category else None
        page = await self.repository.list_current(
            session,
            household_id=household_id,
            search=normalized_search or None,
            category=normalized_category or None,
            include_zero=include_zero,
            sort=sort,
            order=order,
            limit=limit,
            offset=offset,
        )
        return CurrentInventoryListView(
            items=[
                CurrentInventoryView(
                    item_id=record.item.id,
                    name=record.item.name,
                    quantity=record.snapshot.quantity,
                    unit=record.item.default_unit,
                    category=record.item.category,
                    is_active=record.item.is_active,
                    updated_at=record.snapshot.updated_at,
                )
                for record in page.records
            ],
            total=page.total,
        )

    async def get_inventory_detail(
        self,
        session: AsyncSession,
        *,
        household_id: UUID,
        item_id: UUID,
        recent_event_limit: int = 10,
    ) -> InventoryDetailView:
        record = await self.repository.get_by_item_id(session, item_id=item_id)
        if record is None:
            raise item_not_found_error(str(item_id))
        if record.item.household_id != household_id:
            raise household_access_denied_error(str(item_id))

        events = await self.event_repository.list_recent_for_item(
            session,
            household_id=household_id,
            item_id=item_id,
            limit=recent_event_limit,
        )
        return InventoryDetailView(
            item=CurrentInventoryView(
                item_id=record.item.id,
                name=record.item.name,
                quantity=record.snapshot.quantity,
                unit=record.item.default_unit,
                category=record.item.category,
                is_active=record.item.is_active,
                updated_at=record.snapshot.updated_at,
            ),
            recent_events=[self._event_to_view(event) for event in events],
        )

    async def create_inventory_event(
        self,
        session: AsyncSession,
        *,
        household_id: UUID,
        user_id: UUID,
        data: InventoryEventCreate,
    ) -> InventoryEventCreateView:
        async with session.begin():
            record = await self.repository.get_for_update_by_item_id(
                session,
                item_id=data.item_id,
            )
            if record is None:
                raise item_not_found_error(str(data.item_id))
            if record.item.household_id != household_id:
                raise household_access_denied_error(str(data.item_id))
            if not record.item.is_active:
                raise inactive_item_error(str(data.item_id))
            if data.unit != record.item.default_unit:
                raise unit_mismatch_error(
                    str(data.item_id),
                    record.item.default_unit,
                    data.unit,
                )

            signed_quantity = self._signed_quantity(data.event_type, data.quantity)
            previous_quantity = record.snapshot.quantity
            current_quantity = previous_quantity + signed_quantity
            if current_quantity < 0:
                raise insufficient_inventory_error(
                    str(data.item_id),
                    str(previous_quantity),
                    str(data.quantity),
                )

            event = InventoryEvent(
                id=uuid4(),
                household_id=household_id,
                item_id=data.item_id,
                event_type=data.event_type,
                quantity=data.quantity,
                unit=data.unit,
                signed_quantity=signed_quantity,
                created_by=user_id,
                source="manual",
                note=data.note,
            )
            await self.event_repository.add(session, event=event)

            record.snapshot.quantity = current_quantity
            await self.repository.save_snapshot(
                session,
                snapshot=record.snapshot,
            )
            await self.audit_log_repository.add(
                session,
                household_id=household_id,
                user_id=user_id,
                action="inventory_event_created",
                target_type="inventory_event",
                target_id=event.id,
                before_json=None,
                after_json=self._event_audit_state(event),
            )

        return InventoryEventCreateView(
            event_id=event.id,
            item_id=event.item_id,
            event_type=data.event_type,
            quantity=event.quantity,
            signed_quantity=event.signed_quantity,
            previous_quantity=previous_quantity,
            current_quantity=current_quantity,
            created_at=event.created_at,
        )

    async def set_inventory_quantity(
        self,
        session: AsyncSession,
        *,
        household_id: UUID,
        user_id: UUID,
        item_id: UUID,
        data: InventorySetQuantityRequest,
    ) -> InventorySetQuantityView:
        async with session.begin():
            record = await self.repository.get_for_update_by_item_id(
                session,
                item_id=item_id,
            )
            if record is None:
                raise item_not_found_error(str(item_id))
            if record.item.household_id != household_id:
                raise household_access_denied_error(str(item_id))
            if not record.item.is_active:
                raise inactive_item_error(str(item_id))
            if data.unit != record.item.default_unit:
                raise unit_mismatch_error(
                    str(item_id),
                    record.item.default_unit,
                    data.unit,
                )

            previous_quantity = record.snapshot.quantity
            target_quantity = data.quantity
            delta = target_quantity - previous_quantity
            if delta == 0:
                return InventorySetQuantityView(
                    event_id=None,
                    item_id=item_id,
                    previous_quantity=previous_quantity,
                    current_quantity=previous_quantity,
                    changed=False,
                    created_at=None,
                )

            event_type: InventoryEventType = (
                "adjustment_in" if delta > 0 else "adjustment_out"
            )
            quantity = abs(delta)
            signed_quantity = self._signed_quantity(event_type, quantity)

            event = InventoryEvent(
                id=uuid4(),
                household_id=household_id,
                item_id=item_id,
                event_type=event_type,
                quantity=quantity,
                unit=data.unit,
                signed_quantity=signed_quantity,
                created_by=user_id,
                source="manual",
                note=data.note,
            )
            await self.event_repository.add(session, event=event)

            record.snapshot.quantity = target_quantity
            await self.repository.save_snapshot(
                session,
                snapshot=record.snapshot,
            )
            await self.audit_log_repository.add(
                session,
                household_id=household_id,
                user_id=user_id,
                action="inventory_event_created",
                target_type="inventory_event",
                target_id=event.id,
                before_json=None,
                after_json=self._event_audit_state(event),
            )

        return InventorySetQuantityView(
            event_id=event.id,
            item_id=item_id,
            previous_quantity=previous_quantity,
            current_quantity=target_quantity,
            changed=True,
            created_at=event.created_at,
        )

    async def list_inventory_events(
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
    ) -> InventoryEventListView:
        page = await self.event_repository.list_events(
            session,
            household_id=household_id,
            item_id=item_id,
            event_type=event_type,
            source=source,
            created_from=created_from,
            created_to=created_to,
            limit=limit,
            offset=offset,
        )
        return InventoryEventListView(
            items=[
                InventoryEventListEntryView(
                    id=event.id,
                    item_id=event.item_id,
                    event_type=event.event_type,
                    quantity=event.quantity,
                    signed_quantity=event.signed_quantity,
                    unit=event.unit,
                    source=event.source,
                    note=event.note,
                    created_by=event.created_by,
                    created_at=event.created_at,
                )
                for event in page.records
            ],
            total=page.total,
        )

    async def correct_inventory_event(
        self,
        session: AsyncSession,
        *,
        household_id: UUID,
        user_id: UUID,
        event_id: UUID,
        data: InventoryEventCorrectionRequest,
    ) -> InventoryEventCorrectionView:
        async with session.begin():
            original, record = await self._lock_reversible_event(
                session,
                household_id=household_id,
                event_id=event_id,
            )
            if data.unit != record.item.default_unit:
                raise unit_mismatch_error(
                    str(original.item_id),
                    record.item.default_unit,
                    data.unit,
                )

            previous_quantity = record.snapshot.quantity
            reversal_signed = -original.signed_quantity
            replacement_signed = self._signed_quantity(
                data.event_type,
                data.quantity,
            )
            final_quantity = previous_quantity + reversal_signed + replacement_signed
            if final_quantity < 0:
                raise insufficient_inventory_error(
                    str(original.item_id),
                    str(previous_quantity),
                    str(data.quantity),
                )

            reversal = self._build_reversal(original, user_id=user_id)
            await self.event_repository.add(session, event=reversal)
            replacement = InventoryEvent(
                id=uuid4(),
                household_id=household_id,
                item_id=original.item_id,
                event_type=data.event_type,
                quantity=data.quantity,
                unit=data.unit,
                signed_quantity=replacement_signed,
                created_by=user_id,
                source="correction",
                note=data.note,
            )
            await self.event_repository.add(session, event=replacement)

            self._mark_reversed(original, reversal=reversal, user_id=user_id)
            record.snapshot.quantity = final_quantity
            await self.repository.save_snapshot(session, snapshot=record.snapshot)
            await self.audit_log_repository.add(
                session,
                household_id=household_id,
                user_id=user_id,
                action="inventory_event_corrected",
                target_type="inventory_event",
                target_id=original.id,
                before_json=self._event_audit_state(original),
                after_json={
                    "reversal_event_id": str(reversal.id),
                    "replacement_event_id": str(replacement.id),
                    "previous_quantity": str(previous_quantity),
                    "current_quantity": str(final_quantity),
                },
            )

        return InventoryEventCorrectionView(
            original_event_id=original.id,
            reversal_event_id=reversal.id,
            replacement_event_id=replacement.id,
            previous_quantity=previous_quantity,
            current_quantity=final_quantity,
            corrected_at=reversal.created_at,
        )

    async def cancel_inventory_event(
        self,
        session: AsyncSession,
        *,
        household_id: UUID,
        user_id: UUID,
        event_id: UUID,
    ) -> InventoryEventCancellationView:
        async with session.begin():
            original, record = await self._lock_reversible_event(
                session,
                household_id=household_id,
                event_id=event_id,
            )

            previous_quantity = record.snapshot.quantity
            final_quantity = previous_quantity - original.signed_quantity
            if final_quantity < 0:
                raise insufficient_inventory_error(
                    str(original.item_id),
                    str(previous_quantity),
                    str(original.quantity),
                )

            reversal = self._build_reversal(original, user_id=user_id)
            await self.event_repository.add(session, event=reversal)

            self._mark_reversed(original, reversal=reversal, user_id=user_id)
            record.snapshot.quantity = final_quantity
            await self.repository.save_snapshot(session, snapshot=record.snapshot)
            await self.audit_log_repository.add(
                session,
                household_id=household_id,
                user_id=user_id,
                action="inventory_event_reversed",
                target_type="inventory_event",
                target_id=original.id,
                before_json=self._event_audit_state(original),
                after_json={
                    "reversal_event_id": str(reversal.id),
                    "previous_quantity": str(previous_quantity),
                    "current_quantity": str(final_quantity),
                },
            )

        return InventoryEventCancellationView(
            original_event_id=original.id,
            reversal_event_id=reversal.id,
            previous_quantity=previous_quantity,
            current_quantity=final_quantity,
            cancelled_at=reversal.created_at,
        )

    async def rebuild_inventory_snapshot(
        self,
        session: AsyncSession,
        *,
        household_id: UUID,
        item_id: UUID,
    ) -> InventorySnapshotRebuildView:
        """Recompute a Snapshot from the full event ledger.

        Management/recovery helper — not exposed as an external API. Sums every
        event's signed_quantity, including originals and their event_reversals,
        so a reversed original and its reversal offset each other. Cancelled
        originals are never excluded from the sum.
        """
        async with session.begin():
            record = await self.repository.get_for_update_by_item_id(
                session,
                item_id=item_id,
            )
            if record is None:
                raise item_not_found_error(str(item_id))
            if record.item.household_id != household_id:
                raise household_access_denied_error(str(item_id))

            previous_quantity = record.snapshot.quantity
            total = await self.event_repository.sum_signed_quantity(
                session,
                household_id=household_id,
                item_id=item_id,
            )
            if total == previous_quantity:
                return InventorySnapshotRebuildView(
                    item_id=item_id,
                    previous_quantity=previous_quantity,
                    current_quantity=previous_quantity,
                    changed=False,
                )

            record.snapshot.quantity = total
            await self.repository.save_snapshot(session, snapshot=record.snapshot)

        return InventorySnapshotRebuildView(
            item_id=item_id,
            previous_quantity=previous_quantity,
            current_quantity=total,
            changed=True,
        )

    async def _lock_reversible_event(
        self,
        session: AsyncSession,
        *,
        household_id: UUID,
        event_id: UUID,
    ) -> tuple[InventoryEvent, CurrentInventoryRecord]:
        original = await self.event_repository.get_for_update_by_id(
            session,
            event_id=event_id,
        )
        if original is None:
            raise event_not_found_error(str(event_id))
        if original.household_id != household_id:
            raise household_access_denied_error(str(original.item_id))
        if original.reversed_at is not None:
            raise event_already_reversed_error(str(event_id))
        if original.event_type == "event_reversal":
            raise event_not_correctable_error(str(event_id))

        record = await self.repository.get_for_update_by_item_id(
            session,
            item_id=original.item_id,
        )
        if record is None:
            raise item_not_found_error(str(original.item_id))
        return original, record

    @staticmethod
    def _build_reversal(
        original: InventoryEvent,
        *,
        user_id: UUID,
    ) -> InventoryEvent:
        return InventoryEvent(
            id=uuid4(),
            household_id=original.household_id,
            item_id=original.item_id,
            event_type="event_reversal",
            quantity=original.quantity,
            unit=original.unit,
            signed_quantity=-original.signed_quantity,
            created_by=user_id,
            source="correction",
            note=None,
        )

    @staticmethod
    def _mark_reversed(
        original: InventoryEvent,
        *,
        reversal: InventoryEvent,
        user_id: UUID,
    ) -> None:
        original.reversed_at = reversal.created_at
        original.reversed_by = user_id
        original.reversal_event_id = reversal.id

    @staticmethod
    def _event_to_view(event: InventoryEvent) -> RecentInventoryEventView:
        return RecentInventoryEventView(
            id=event.id,
            event_type=event.event_type,
            quantity=event.quantity,
            signed_quantity=event.signed_quantity,
            unit=event.unit,
            created_at=event.created_at,
        )

    @staticmethod
    def _signed_quantity(
        event_type: InventoryEventType,
        quantity: Decimal,
    ) -> Decimal:
        if event_type in {"stock_in", "adjustment_in", "initial_stock"}:
            return quantity
        return -quantity

    @staticmethod
    def _event_audit_state(event: InventoryEvent) -> dict[str, Any]:
        return {
            "item_id": str(event.item_id),
            "event_type": event.event_type,
            "quantity": str(event.quantity),
            "signed_quantity": str(event.signed_quantity),
            "unit": event.unit,
            "source": event.source,
            "note": event.note,
        }


inventory_service = InventoryService(
    InventoryRepository(),
    InventoryEventRepository(),
    AuditLogRepository(),
)


def get_inventory_service() -> InventoryService:
    return inventory_service
