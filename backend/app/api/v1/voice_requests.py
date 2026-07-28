from typing import Annotated

from fastapi import APIRouter, Depends, status

from app.api.dependencies import CurrentHouseholdId, DatabaseSession
from app.schemas.voice_request import (
    TextVoiceRequestCreate,
    TextVoiceRequestResponse,
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
