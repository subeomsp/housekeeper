from datetime import UTC, datetime
from types import TracebackType
from typing import cast
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.models import VoiceRequest
from app.repositories.voice_request_repository import VoiceRequestRepository
from app.schemas.voice_request import TextVoiceRequestCreate
from app.services.voice_request_service import VoiceRequestService

HOUSEHOLD_ID = UUID("00000000-0000-4000-8000-000000000099")
REQUEST_ID = UUID("00000000-0000-4000-8000-000000000501")
CREATED_AT = datetime(2026, 7, 28, 12, 0, tzinfo=UTC)


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


class FakeVoiceRequestRepository(VoiceRequestRepository):
    def __init__(self) -> None:
        self.added: VoiceRequest | None = None

    async def add(
        self,
        session: AsyncSession,
        *,
        voice_request: VoiceRequest,
    ) -> None:
        voice_request.id = REQUEST_ID
        voice_request.created_at = CREATED_AT
        self.added = voice_request


async def test_text_request_is_stored_for_planning_without_inventory_changes() -> None:
    repository = FakeVoiceRequestRepository()
    service = VoiceRequestService(repository)

    result = await service.create_text_request(
        cast(AsyncSession, FakeSession()),
        household_id=HOUSEHOLD_ID,
        data=TextVoiceRequestCreate(transcript=" 우유 두 개 사왔어. "),
    )

    assert repository.added is not None
    assert repository.added.household_id == HOUSEHOLD_ID
    assert repository.added.transcript == "우유 두 개 사왔어."
    assert repository.added.audio_path is None
    assert repository.added.status == "planning"
    assert result.request_id == REQUEST_ID
    assert result.status == "planning"
