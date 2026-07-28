from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.models import VoiceRequest
from app.repositories.voice_request_repository import VoiceRequestRepository
from app.schemas.voice_request import (
    TextVoiceRequestCreate,
    VoiceRequestStatus,
)


@dataclass(frozen=True)
class TextVoiceRequestView:
    request_id: UUID
    transcript: str
    status: VoiceRequestStatus
    created_at: datetime


class VoiceRequestService:
    def __init__(self, repository: VoiceRequestRepository) -> None:
        self.repository = repository

    async def create_text_request(
        self,
        session: AsyncSession,
        *,
        household_id: UUID,
        data: TextVoiceRequestCreate,
    ) -> TextVoiceRequestView:
        voice_request = VoiceRequest(
            household_id=household_id,
            transcript=data.transcript,
            audio_path=None,
            status="planning",
        )
        async with session.begin():
            await self.repository.add(
                session,
                voice_request=voice_request,
            )

        return TextVoiceRequestView(
            request_id=voice_request.id,
            transcript=data.transcript,
            status="planning",
            created_at=voice_request.created_at,
        )


voice_request_service = VoiceRequestService(VoiceRequestRepository())


def get_voice_request_service() -> VoiceRequestService:
    return voice_request_service
