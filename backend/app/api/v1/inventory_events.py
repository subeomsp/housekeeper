from datetime import datetime
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query, status

from app.api.dependencies import CurrentHouseholdId, CurrentUserId, DatabaseSession
from app.schemas.inventory_event import (
    EventSource,
    InventoryEventCancellationResponse,
    InventoryEventCorrectionRequest,
    InventoryEventCorrectionResponse,
    InventoryEventCreate,
    InventoryEventCreateResponse,
    InventoryEventListEntry,
    InventoryEventListResponse,
    StoredEventType,
)
from app.services.inventory_service import InventoryService, get_inventory_service

router = APIRouter(tags=["inventory-events"])
InventoryServiceDependency = Annotated[
    InventoryService,
    Depends(get_inventory_service),
]


@router.post(
    "",
    response_model=InventoryEventCreateResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_inventory_event(
    data: InventoryEventCreate,
    session: DatabaseSession,
    household_id: CurrentHouseholdId,
    user_id: CurrentUserId,
    service: InventoryServiceDependency,
) -> InventoryEventCreateResponse:
    result = await service.create_inventory_event(
        session,
        household_id=household_id,
        user_id=user_id,
        data=data,
    )
    return InventoryEventCreateResponse(
        event_id=result.event_id,
        item_id=result.item_id,
        event_type=result.event_type,
        quantity=result.quantity,
        signed_quantity=result.signed_quantity,
        previous_quantity=result.previous_quantity,
        current_quantity=result.current_quantity,
        created_at=result.created_at,
    )


@router.get("", response_model=InventoryEventListResponse)
async def list_inventory_events(
    session: DatabaseSession,
    household_id: CurrentHouseholdId,
    service: InventoryServiceDependency,
    item_id: UUID | None = None,
    event_type: StoredEventType | None = None,
    source: EventSource | None = None,
    created_from: Annotated[datetime | None, Query(alias="from")] = None,
    created_to: Annotated[datetime | None, Query(alias="to")] = None,
    limit: Annotated[int, Query(ge=1, le=100)] = 50,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> InventoryEventListResponse:
    result = await service.list_inventory_events(
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
    return InventoryEventListResponse(
        items=[
            InventoryEventListEntry(
                id=entry.id,
                item_id=entry.item_id,
                event_type=entry.event_type,
                quantity=entry.quantity,
                signed_quantity=entry.signed_quantity,
                unit=entry.unit,
                source=entry.source,
                note=entry.note,
                created_by=entry.created_by,
                created_at=entry.created_at,
            )
            for entry in result.items
        ],
        total=result.total,
    )


@router.patch("/{event_id}", response_model=InventoryEventCorrectionResponse)
async def correct_inventory_event(
    event_id: UUID,
    data: InventoryEventCorrectionRequest,
    session: DatabaseSession,
    household_id: CurrentHouseholdId,
    user_id: CurrentUserId,
    service: InventoryServiceDependency,
) -> InventoryEventCorrectionResponse:
    result = await service.correct_inventory_event(
        session,
        household_id=household_id,
        user_id=user_id,
        event_id=event_id,
        data=data,
    )
    return InventoryEventCorrectionResponse(
        original_event_id=result.original_event_id,
        reversal_event_id=result.reversal_event_id,
        replacement_event_id=result.replacement_event_id,
        previous_quantity=result.previous_quantity,
        current_quantity=result.current_quantity,
        corrected_at=result.corrected_at,
    )


@router.delete("/{event_id}", response_model=InventoryEventCancellationResponse)
async def cancel_inventory_event(
    event_id: UUID,
    session: DatabaseSession,
    household_id: CurrentHouseholdId,
    user_id: CurrentUserId,
    service: InventoryServiceDependency,
) -> InventoryEventCancellationResponse:
    result = await service.cancel_inventory_event(
        session,
        household_id=household_id,
        user_id=user_id,
        event_id=event_id,
    )
    return InventoryEventCancellationResponse(
        original_event_id=result.original_event_id,
        reversal_event_id=result.reversal_event_id,
        previous_quantity=result.previous_quantity,
        current_quantity=result.current_quantity,
        cancelled_at=result.cancelled_at,
    )

