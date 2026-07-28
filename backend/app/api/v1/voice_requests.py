from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, status

from app.api.dependencies import CurrentHouseholdId, DatabaseSession
from app.providers import (
    InventoryPlannerProvider,
    get_inventory_planner_provider,
)
from app.schemas.action_plan import ActionPlanResponse
from app.schemas.voice_request import (
    TextVoiceRequestCreate,
    TextVoiceRequestResponse,
)
from app.services.action_plan_service import (
    ActionPlanService,
    get_action_plan_service,
)
from app.services.voice_request_service import (
    VoiceRequestService,
    get_voice_request_service,
)

router = APIRouter(tags=["voice-requests"])
VoiceRequestServiceDependency = Annotated[
    VoiceRequestService,
    Depends(get_voice_request_service),
]
ActionPlanServiceDependency = Annotated[
    ActionPlanService,
    Depends(get_action_plan_service),
]
InventoryPlannerDependency = Annotated[
    InventoryPlannerProvider,
    Depends(get_inventory_planner_provider),
]


@router.post(
    "/text",
    response_model=TextVoiceRequestResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_text_voice_request(
    data: TextVoiceRequestCreate,
    session: DatabaseSession,
    household_id: CurrentHouseholdId,
    service: VoiceRequestServiceDependency,
) -> TextVoiceRequestResponse:
    result = await service.create_text_request(
        session,
        household_id=household_id,
        data=data,
    )
    return TextVoiceRequestResponse(
        request_id=result.request_id,
        transcript=result.transcript,
        status=result.status,
        created_at=result.created_at,
    )


@router.post(
    "/{request_id}/action-plan",
    response_model=ActionPlanResponse,
    status_code=status.HTTP_201_CREATED,
)
async def generate_action_plan(
    request_id: UUID,
    session: DatabaseSession,
    household_id: CurrentHouseholdId,
    service: ActionPlanServiceDependency,
    provider: InventoryPlannerDependency,
) -> ActionPlanResponse:
    result = await service.generate(
        session,
        household_id=household_id,
        request_id=request_id,
        provider=provider,
    )
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
