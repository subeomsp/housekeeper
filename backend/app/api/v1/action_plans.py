from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends

from app.api.dependencies import CurrentHouseholdId, CurrentUserId, DatabaseSession
from app.schemas.action_plan import (
    ActionPlanActionUpdate,
    ActionPlanExecutionResponse,
    ActionPlanNewItemUpdate,
    ActionPlanResponse,
)
from app.services.action_plan_service import (
    ActionPlanService,
    ActionPlanView,
    get_action_plan_service,
)

router = APIRouter(tags=["action-plans"])
ActionPlanServiceDependency = Annotated[
    ActionPlanService,
    Depends(get_action_plan_service),
]


@router.get("/{request_id}", response_model=ActionPlanResponse)
async def get_action_plan(
    request_id: UUID,
    session: DatabaseSession,
    household_id: CurrentHouseholdId,
    service: ActionPlanServiceDependency,
) -> ActionPlanResponse:
    result = await service.get(
        session,
        household_id=household_id,
        request_id=request_id,
    )
    return _response(result)


@router.patch(
    "/{request_id}/actions/{action_id}",
    response_model=ActionPlanResponse,
)
async def update_action_plan_action(
    request_id: UUID,
    action_id: str,
    data: ActionPlanActionUpdate,
    session: DatabaseSession,
    household_id: CurrentHouseholdId,
    service: ActionPlanServiceDependency,
) -> ActionPlanResponse:
    result = await service.update_action(
        session,
        household_id=household_id,
        request_id=request_id,
        action_id=action_id,
        data=data,
    )
    return _response(result)


@router.post(
    "/{request_id}/actions/{action_id}/new-item",
    response_model=ActionPlanResponse,
)
async def resolve_action_plan_new_item(
    request_id: UUID,
    action_id: str,
    data: ActionPlanNewItemUpdate,
    session: DatabaseSession,
    household_id: CurrentHouseholdId,
    service: ActionPlanServiceDependency,
) -> ActionPlanResponse:
    result = await service.resolve_new_item(
        session,
        household_id=household_id,
        request_id=request_id,
        action_id=action_id,
        data=data,
    )
    return _response(result)


@router.delete(
    "/{request_id}/actions/{action_id}",
    response_model=ActionPlanResponse,
)
async def delete_action_plan_action(
    request_id: UUID,
    action_id: str,
    session: DatabaseSession,
    household_id: CurrentHouseholdId,
    service: ActionPlanServiceDependency,
) -> ActionPlanResponse:
    result = await service.delete_action(
        session,
        household_id=household_id,
        request_id=request_id,
        action_id=action_id,
    )
    return _response(result)


@router.post(
    "/{request_id}/execute",
    response_model=ActionPlanExecutionResponse,
)
async def execute_action_plan(
    request_id: UUID,
    session: DatabaseSession,
    household_id: CurrentHouseholdId,
    user_id: CurrentUserId,
    service: ActionPlanServiceDependency,
) -> ActionPlanExecutionResponse:
    result = await service.execute(
        session,
        household_id=household_id,
        user_id=user_id,
        request_id=request_id,
    )
    return ActionPlanExecutionResponse(
        inventory_updated=result.inventory_updated,
        event_count=result.event_count,
        already_executed=result.already_executed,
    )


def _response(result: ActionPlanView) -> ActionPlanResponse:
    return ActionPlanResponse(
        request_id=result.request_id,
        plan_id=result.plan_id,
        version=result.payload.version,
        transcript=result.payload.transcript,
        summary=result.payload.summary,
        requires_confirmation=result.payload.requires_confirmation,
        actions=result.payload.actions,
        approved=result.approved,
        executed=result.executed,
        created_at=result.created_at,
    )
