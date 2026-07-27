from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from typing import Any
from uuid import UUID, uuid4

from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import (
    duplicate_item_name_error,
    household_access_denied_error,
    item_has_inventory_error,
    item_not_found_error,
    unit_change_requires_zero_inventory_error,
)
from app.models import Inventory, InventoryItem
from app.repositories.audit_log_repository import AuditLogRepository
from app.repositories.inventory_item_repository import (
    InventoryItemRecord,
    InventoryItemRepository,
)
from app.schemas.inventory_item import InventoryItemCreate, InventoryItemUpdate


def normalize_item_name(name: str) -> str:
    return "".join(character for character in name.strip().lower() if character.isalnum())


@dataclass(frozen=True)
class InventoryItemView:
    id: UUID
    name: str
    default_unit: str
    category: str | None
    is_active: bool
    current_quantity: Decimal
    created_at: datetime
    updated_at: datetime


@dataclass(frozen=True)
class InventoryItemListView:
    items: list[InventoryItemView]
    total: int


class InventoryItemService:
    def __init__(
        self,
        repository: InventoryItemRepository,
        audit_log_repository: AuditLogRepository,
    ) -> None:
        self.repository = repository
        self.audit_log_repository = audit_log_repository

    async def create_item(
        self,
        session: AsyncSession,
        *,
        household_id: UUID,
        user_id: UUID,
        data: InventoryItemCreate,
    ) -> InventoryItemView:
        normalized_name = normalize_item_name(data.name)

        try:
            async with session.begin():
                if await self.repository.normalized_name_exists(
                    session,
                    household_id=household_id,
                    normalized_name=normalized_name,
                ):
                    raise duplicate_item_name_error(data.name)

                item = InventoryItem(
                    id=uuid4(),
                    household_id=household_id,
                    name=data.name,
                    normalized_name=normalized_name,
                    default_unit=data.default_unit,
                    category=data.category,
                    is_active=True,
                )
                snapshot = Inventory(
                    id=uuid4(),
                    household_id=household_id,
                    item_id=item.id,
                    quantity=Decimal("0"),
                )
                await self.repository.add_with_snapshot(
                    session,
                    item=item,
                    snapshot=snapshot,
                )
                await self.audit_log_repository.add(
                    session,
                    household_id=household_id,
                    user_id=user_id,
                    action="inventory_item_created",
                    target_type="inventory_item",
                    target_id=item.id,
                    before_json=None,
                    after_json=self._audit_state(item),
                )
        except IntegrityError as exception:
            if self._constraint_name(exception) == "uq_inventory_item_name":
                raise duplicate_item_name_error(data.name) from exception
            raise

        return self._to_view(item, Decimal("0"))

    async def list_items(
        self,
        session: AsyncSession,
        *,
        household_id: UUID,
        search: str | None,
        category: str | None,
        include_inactive: bool,
        limit: int,
        offset: int,
    ) -> InventoryItemListView:
        normalized_search = normalize_item_name(search) if search else None
        normalized_category = category.strip() if category else None
        page = await self.repository.list_with_quantity(
            session,
            household_id=household_id,
            search=normalized_search or None,
            category=normalized_category or None,
            include_inactive=include_inactive,
            limit=limit,
            offset=offset,
        )
        return InventoryItemListView(
            items=[
                self._to_view(record.item, record.current_quantity)
                for record in page.records
            ],
            total=page.total,
        )

    async def update_item(
        self,
        session: AsyncSession,
        *,
        household_id: UUID,
        user_id: UUID,
        item_id: UUID,
        data: InventoryItemUpdate,
    ) -> InventoryItemView:
        try:
            async with session.begin():
                record = await self._get_accessible_item_for_update(
                    session,
                    household_id=household_id,
                    item_id=item_id,
                )
                item = record.item
                before_json = self._audit_state(item)

                if data.name is not None:
                    normalized_name = normalize_item_name(data.name)
                    if await self.repository.normalized_name_exists(
                        session,
                        household_id=household_id,
                        normalized_name=normalized_name,
                        exclude_item_id=item.id,
                    ):
                        raise duplicate_item_name_error(data.name)
                    item.name = data.name
                    item.normalized_name = normalized_name

                if (
                    data.default_unit is not None
                    and data.default_unit != item.default_unit
                ):
                    if record.current_quantity != 0:
                        raise unit_change_requires_zero_inventory_error(
                            str(item.id),
                            str(record.current_quantity),
                        )
                    item.default_unit = data.default_unit

                if "category" in data.model_fields_set:
                    item.category = data.category

                await self.repository.save(session, item=item)
                after_json = self._audit_state(item)
                if before_json != after_json:
                    await self.audit_log_repository.add(
                        session,
                        household_id=household_id,
                        user_id=user_id,
                        action="inventory_item_updated",
                        target_type="inventory_item",
                        target_id=item.id,
                        before_json=before_json,
                        after_json=after_json,
                    )
        except IntegrityError as exception:
            if self._constraint_name(exception) == "uq_inventory_item_name":
                raise duplicate_item_name_error(data.name or "") from exception
            raise

        return self._to_view(item, record.current_quantity)

    async def archive_item(
        self,
        session: AsyncSession,
        *,
        household_id: UUID,
        user_id: UUID,
        item_id: UUID,
    ) -> InventoryItemView:
        async with session.begin():
            record = await self._get_accessible_item_for_update(
                session,
                household_id=household_id,
                item_id=item_id,
            )
            if record.current_quantity != 0:
                raise item_has_inventory_error(
                    str(item_id),
                    str(record.current_quantity),
                )
            before_json = self._audit_state(record.item)
            record.item.is_active = False
            await self.repository.save(session, item=record.item)
            after_json = self._audit_state(record.item)
            if before_json != after_json:
                await self.audit_log_repository.add(
                    session,
                    household_id=household_id,
                    user_id=user_id,
                    action="inventory_item_archived",
                    target_type="inventory_item",
                    target_id=record.item.id,
                    before_json=before_json,
                    after_json=after_json,
                )

        return self._to_view(record.item, record.current_quantity)

    async def restore_item(
        self,
        session: AsyncSession,
        *,
        household_id: UUID,
        user_id: UUID,
        item_id: UUID,
    ) -> InventoryItemView:
        async with session.begin():
            record = await self._get_accessible_item_for_update(
                session,
                household_id=household_id,
                item_id=item_id,
            )
            before_json = self._audit_state(record.item)
            record.item.is_active = True
            await self.repository.save(session, item=record.item)
            after_json = self._audit_state(record.item)
            if before_json != after_json:
                await self.audit_log_repository.add(
                    session,
                    household_id=household_id,
                    user_id=user_id,
                    action="inventory_item_restored",
                    target_type="inventory_item",
                    target_id=record.item.id,
                    before_json=before_json,
                    after_json=after_json,
                )

        return self._to_view(record.item, record.current_quantity)

    async def _get_accessible_item_for_update(
        self,
        session: AsyncSession,
        *,
        household_id: UUID,
        item_id: UUID,
    ) -> InventoryItemRecord:
        record = await self.repository.get_with_quantity_for_update(
            session,
            item_id=item_id,
        )
        if record is None:
            raise item_not_found_error(str(item_id))
        if record.item.household_id != household_id:
            raise household_access_denied_error(str(item_id))
        return record

    @staticmethod
    def _to_view(item: InventoryItem, quantity: Decimal) -> InventoryItemView:
        return InventoryItemView(
            id=item.id,
            name=item.name,
            default_unit=item.default_unit,
            category=item.category,
            is_active=item.is_active,
            current_quantity=quantity,
            created_at=item.created_at,
            updated_at=item.updated_at,
        )

    @staticmethod
    def _constraint_name(exception: IntegrityError) -> str | None:
        cause = getattr(exception.orig, "__cause__", None)
        return getattr(exception.orig, "constraint_name", None) or getattr(
            cause,
            "constraint_name",
            None,
        )

    @staticmethod
    def _audit_state(item: InventoryItem) -> dict[str, Any]:
        return {
            "name": item.name,
            "normalized_name": item.normalized_name,
            "default_unit": item.default_unit,
            "category": item.category,
            "is_active": item.is_active,
        }


inventory_item_service = InventoryItemService(
    InventoryItemRepository(),
    AuditLogRepository(),
)


def get_inventory_item_service() -> InventoryItemService:
    return inventory_item_service
