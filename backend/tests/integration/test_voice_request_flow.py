from uuid import UUID

import pytest
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import ActionPlan, Household, InventoryEvent, VoiceRequest
from app.repositories.voice_request_repository import VoiceRequestRepository
from app.schemas.voice_request import TextVoiceRequestCreate
from app.services.voice_request_service import VoiceRequestService

HOUSEHOLD_ID = UUID("00000000-0000-4000-8000-0000000005a1")


@pytest.fixture
async def household(db_session: AsyncSession) -> UUID:
    async with db_session.begin():
        db_session.add(Household(id=HOUSEHOLD_ID, name="우리 집"))
    return HOUSEHOLD_ID


async def test_text_request_commits_without_action_plan_or_inventory_change(
    db_session: AsyncSession,
    household: UUID,
) -> None:
    result = await VoiceRequestService(VoiceRequestRepository()).create_text_request(
        db_session,
        household_id=household,
        data=TextVoiceRequestCreate(transcript="우유 두 개 사왔어."),
    )

    stored = await db_session.scalar(
        select(VoiceRequest).where(VoiceRequest.id == result.request_id)
    )
    assert stored is not None
    assert stored.household_id == household
    assert stored.transcript == "우유 두 개 사왔어."
    assert stored.status == "planning"
    action_plan_count = await db_session.scalar(select(func.count()).select_from(ActionPlan))
    inventory_event_count = await db_session.scalar(
        select(func.count()).select_from(InventoryEvent)
    )
    assert action_plan_count == 0
    assert inventory_event_count == 0
