from uuid import UUID

import pytest
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import (
    ActionPlan,
    Household,
    Inventory,
    InventoryEvent,
    InventoryItem,
    VoiceRequest,
)
from app.repositories.action_plan_repository import ActionPlanRepository
from app.repositories.inventory_item_repository import InventoryItemRepository
from app.repositories.voice_request_repository import VoiceRequestRepository
from app.schemas.action_plan import (
    ActionPlanActionUpdate,
    ActionPlanPayload,
    PlannerInventoryItem,
)
from app.schemas.voice_request import TextVoiceRequestCreate
from app.services.action_plan_service import ActionPlanService, ActionPlanValidator
from app.services.voice_request_service import VoiceRequestService

HOUSEHOLD_ID = UUID("00000000-0000-4000-8000-0000000005a1")
ITEM_ID = UUID("00000000-0000-4000-8000-0000000005a2")


@pytest.fixture
async def household(db_session: AsyncSession) -> UUID:
    async with db_session.begin():
        db_session.add(Household(id=HOUSEHOLD_ID, name="우리 집"))
        await db_session.flush()
        db_session.add(
            InventoryItem(
                id=ITEM_ID,
                household_id=HOUSEHOLD_ID,
                name="우유",
                normalized_name="우유",
                default_unit="개",
                is_active=True,
            )
        )
        await db_session.flush()
        db_session.add(
            Inventory(
                household_id=HOUSEHOLD_ID,
                item_id=ITEM_ID,
                quantity=5,
            )
        )
    return HOUSEHOLD_ID


class FakePlanner:
    async def create_action_plan(
        self,
        *,
        transcript: str,
        inventory_context: list[PlannerInventoryItem],
    ) -> ActionPlanPayload:
        return ActionPlanPayload.model_validate(
            {
                "version": "1.0",
                "transcript": transcript,
                "summary": "우유 2개 입고",
                "requires_confirmation": True,
                "actions": [
                    {
                        "action_id": "a1",
                        "type": "stock_in",
                        "item": {
                            "raw_name": "우유",
                            "matched_item_id": inventory_context[0].item_id,
                            "matched_name": inventory_context[0].name,
                            "is_new_item": False,
                        },
                        "quantity": {
                            "raw_value": 2,
                            "raw_unit": "개",
                            "normalized_value": 2,
                            "normalized_unit": "개",
                            "conversion_applied": False,
                            "conversion_reason": None,
                        },
                        "confidence": 0.98,
                        "warnings": [],
                        "requires_user_input": False,
                    }
                ],
            }
        )


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


async def test_action_plan_is_saved_without_inventory_mutation(
    db_session: AsyncSession,
    household: UUID,
) -> None:
    request = await VoiceRequestService(VoiceRequestRepository()).create_text_request(
        db_session,
        household_id=household,
        data=TextVoiceRequestCreate(transcript="우유 두 개 사왔어."),
    )
    service = ActionPlanService(
        voice_request_repository=VoiceRequestRepository(),
        action_plan_repository=ActionPlanRepository(),
        inventory_item_repository=InventoryItemRepository(),
        validator=ActionPlanValidator(),
    )

    result = await service.generate(
        db_session,
        household_id=household,
        request_id=request.request_id,
        provider=FakePlanner(),
    )

    stored_request = await db_session.scalar(
        select(VoiceRequest).where(VoiceRequest.id == request.request_id)
    )
    stored_plan = await db_session.scalar(select(ActionPlan).where(ActionPlan.id == result.plan_id))
    inventory_event_count = await db_session.scalar(
        select(func.count()).select_from(InventoryEvent)
    )
    snapshot = await db_session.scalar(select(Inventory).where(Inventory.item_id == ITEM_ID))
    assert stored_request is not None
    assert stored_request.status == "waiting_confirmation"
    assert stored_plan is not None
    assert stored_plan.approved is False
    assert stored_plan.executed is False
    assert inventory_event_count == 0
    assert snapshot is not None
    assert snapshot.quantity == 5

    await db_session.rollback()
    updated = await service.update_action(
        db_session,
        household_id=household,
        request_id=request.request_id,
        action_id="a1",
        data=ActionPlanActionUpdate(
            type="set_quantity",
            item_id=ITEM_ID,
            quantity=0,
            unit="개",
        ),
    )

    assert updated.payload.actions[0].type == "set_quantity"
    assert updated.payload.actions[0].quantity.normalized_value == 0
    unchanged_snapshot = await db_session.scalar(
        select(Inventory).where(Inventory.item_id == ITEM_ID)
    )
    unchanged_event_count = await db_session.scalar(
        select(func.count()).select_from(InventoryEvent)
    )
    assert unchanged_snapshot is not None
    assert unchanged_snapshot.quantity == 5
    assert unchanged_event_count == 0
