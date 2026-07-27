from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query

from app.api.dependencies import (
    CurrentHouseholdId,
    CurrentUserId,
    DatabaseSession,
)
from app.schemas.inventory import (
    InventoryDetailResponse,
    InventoryListEntry,
    InventoryListResponse,
    InventorySetQuantityRequest,
    InventorySetQuantityResponse,
    InventorySort,
    RecentInventoryEvent,
    SortOrder,
)
from app.services.inventory_service import InventoryService, get_inventory_service

router = APIRouter(tags=["inventory"])
InventoryServiceDependency = Annotated[
    InventoryService,
    Depends(get_inventory_service),
]


@router.get("", response_model=InventoryListResponse)
async def list_current_inventory(
    session: DatabaseSession,
    household_id: CurrentHouseholdId,
    service: InventoryServiceDependency,
    search: Annotated[str | None, Query(max_length=100)] = None,
    category: Annotated[str | None, Query(max_length=50)] = None,
    include_zero: bool = True,
    sort: InventorySort = "updated_at",
    order: SortOrder = "desc",
    limit: Annotated[int, Query(ge=1, le=100)] = 50,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> InventoryListResponse:
    result = await service.list_current_inventory(
        session,
        household_id=household_id,
        search=search,
        category=category,
        include_zero=include_zero,
        sort=sort,
        order=order,
        limit=limit,
        offset=offset,
    )
    return InventoryListResponse(
        items=[
            InventoryListEntry(
                item_id=item.item_id,
                name=item.name,
                quantity=item.quantity,
                unit=item.unit,
                category=item.category,
                is_active=item.is_active,
                updated_at=item.updated_at,
            )
            for item in result.items
        ],
        total=result.total,
    )


@router.get("/{item_id}", response_model=InventoryDetailResponse)
async def get_inventory_detail(
    item_id: UUID,
    session: DatabaseSession,
    household_id: CurrentHouseholdId,
    service: InventoryServiceDependency,
) -> InventoryDetailResponse:
    detail = await service.get_inventory_detail(
        session,
        household_id=household_id,
        item_id=item_id,
    )
    item = detail.item
    return InventoryDetailResponse(
        item_id=item.item_id,
        name=item.name,
        quantity=item.quantity,
        unit=item.unit,
        category=item.category,
        is_active=item.is_active,
        updated_at=item.updated_at,
        recent_events=[
            RecentInventoryEvent(
                id=event.id,
                event_type=event.event_type,
                quantity=event.quantity,
                signed_quantity=event.signed_quantity,
                unit=event.unit,
                created_at=event.created_at,
            )
            for event in detail.recent_events
        ],
    )


@router.put("/{item_id}/quantity", response_model=InventorySetQuantityResponse)
async def set_inventory_quantity(
    item_id: UUID,
    data: InventorySetQuantityRequest,
    session: DatabaseSession,
    household_id: CurrentHouseholdId,
    user_id: CurrentUserId,
    service: InventoryServiceDependency,
) -> InventorySetQuantityResponse:
    result = await service.set_inventory_quantity(
        session,
        household_id=household_id,
        user_id=user_id,
        item_id=item_id,
        data=data,
    )
    return InventorySetQuantityResponse(
        event_id=result.event_id,
        item_id=result.item_id,
        previous_quantity=result.previous_quantity,
        current_quantity=result.current_quantity,
        changed=result.changed,
        created_at=result.created_at,
    )

