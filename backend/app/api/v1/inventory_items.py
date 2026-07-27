from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query, status

from app.api.dependencies import CurrentHouseholdId, CurrentUserId, DatabaseSession
from app.schemas.inventory_item import (
    InventoryItemCreate,
    InventoryItemListEntry,
    InventoryItemListResponse,
    InventoryItemMutationResponse,
    InventoryItemResponse,
    InventoryItemUpdate,
)
from app.services.inventory_item_service import (
    InventoryItemService,
    InventoryItemView,
    get_inventory_item_service,
)

router = APIRouter(tags=["inventory-items"])
InventoryItemServiceDependency = Annotated[
    InventoryItemService,
    Depends(get_inventory_item_service),
]


def to_mutation_response(item: InventoryItemView) -> InventoryItemMutationResponse:
    return InventoryItemMutationResponse(
        id=item.id,
        name=item.name,
        default_unit=item.default_unit,
        category=item.category,
        is_active=item.is_active,
        current_quantity=item.current_quantity,
        updated_at=item.updated_at,
    )


@router.post("", response_model=InventoryItemResponse, status_code=status.HTTP_201_CREATED)
async def create_inventory_item(
    data: InventoryItemCreate,
    session: DatabaseSession,
    household_id: CurrentHouseholdId,
    user_id: CurrentUserId,
    service: InventoryItemServiceDependency,
) -> InventoryItemResponse:
    item = await service.create_item(
        session,
        household_id=household_id,
        user_id=user_id,
        data=data,
    )
    return InventoryItemResponse(
        id=item.id,
        name=item.name,
        default_unit=item.default_unit,
        category=item.category,
        is_active=item.is_active,
        current_quantity=item.current_quantity,
        created_at=item.created_at,
    )


@router.get("", response_model=InventoryItemListResponse)
async def list_inventory_items(
    session: DatabaseSession,
    household_id: CurrentHouseholdId,
    service: InventoryItemServiceDependency,
    search: Annotated[str | None, Query(max_length=100)] = None,
    category: Annotated[str | None, Query(max_length=50)] = None,
    include_inactive: bool = False,
    limit: Annotated[int, Query(ge=1, le=100)] = 50,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> InventoryItemListResponse:
    result = await service.list_items(
        session,
        household_id=household_id,
        search=search,
        category=category,
        include_inactive=include_inactive,
        limit=limit,
        offset=offset,
    )
    return InventoryItemListResponse(
        items=[
            InventoryItemListEntry(
                id=item.id,
                name=item.name,
                default_unit=item.default_unit,
                category=item.category,
                is_active=item.is_active,
                current_quantity=item.current_quantity,
            )
            for item in result.items
        ],
        total=result.total,
    )


@router.patch("/{item_id}", response_model=InventoryItemMutationResponse)
async def update_inventory_item(
    item_id: UUID,
    data: InventoryItemUpdate,
    session: DatabaseSession,
    household_id: CurrentHouseholdId,
    user_id: CurrentUserId,
    service: InventoryItemServiceDependency,
) -> InventoryItemMutationResponse:
    item = await service.update_item(
        session,
        household_id=household_id,
        user_id=user_id,
        item_id=item_id,
        data=data,
    )
    return to_mutation_response(item)


@router.delete("/{item_id}", response_model=InventoryItemMutationResponse)
async def archive_inventory_item(
    item_id: UUID,
    session: DatabaseSession,
    household_id: CurrentHouseholdId,
    user_id: CurrentUserId,
    service: InventoryItemServiceDependency,
) -> InventoryItemMutationResponse:
    item = await service.archive_item(
        session,
        household_id=household_id,
        user_id=user_id,
        item_id=item_id,
    )
    return to_mutation_response(item)


@router.post("/{item_id}/restore", response_model=InventoryItemMutationResponse)
async def restore_inventory_item(
    item_id: UUID,
    session: DatabaseSession,
    household_id: CurrentHouseholdId,
    user_id: CurrentUserId,
    service: InventoryItemServiceDependency,
) -> InventoryItemMutationResponse:
    item = await service.restore_item(
        session,
        household_id=household_id,
        user_id=user_id,
        item_id=item_id,
    )
    return to_mutation_response(item)
