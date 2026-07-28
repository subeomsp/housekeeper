from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock
from uuid import UUID

from fastapi import FastAPI
from httpx import AsyncClient

from app.providers import get_inventory_planner_provider
from app.schemas.action_plan import ActionPlanPayload
from app.services.action_plan_service import (
    ActionPlanService,
    ActionPlanView,
    get_action_plan_service,
)
from app.services.voice_request_service import (
    TextVoiceRequestView,
    VoiceRequestService,
    get_voice_request_service,
)

REQUEST_ID = UUID("00000000-0000-4000-8000-000000000501")
CREATED_AT = datetime(2026, 7, 28, 12, 0, tzinfo=UTC)
PLAN_ID = UUID("00000000-0000-4000-8000-000000000601")


async def test_create_text_voice_request_returns_planning_request(
    app: FastAPI,
    client: AsyncClient,
) -> None:
    service = MagicMock(spec=VoiceRequestService)
    service.create_text_request = AsyncMock(
        return_value=TextVoiceRequestView(
            request_id=REQUEST_ID,
            transcript="우유 두 개 사왔어.",
            status="planning",
            created_at=CREATED_AT,
        )
    )
    app.dependency_overrides[get_voice_request_service] = lambda: service

    response = await client.post(
        "/api/v1/voice-requests/text",
        json={"transcript": " 우유 두 개 사왔어. "},
    )

    assert response.status_code == 201
    assert response.json() == {
        "request_id": str(REQUEST_ID),
        "transcript": "우유 두 개 사왔어.",
        "status": "planning",
        "created_at": "2026-07-28T12:00:00Z",
    }
    service.create_text_request.assert_awaited_once()


async def test_create_text_voice_request_rejects_blank_transcript(
    client: AsyncClient,
) -> None:
    response = await client.post(
        "/api/v1/voice-requests/text",
        json={"transcript": "   "},
    )

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "VALIDATION_ERROR"


async def test_generate_action_plan_returns_confirmation_payload(
    app: FastAPI,
    client: AsyncClient,
) -> None:
    payload = ActionPlanPayload.model_validate(
        {
            "version": "1.0",
            "transcript": "우유 두 개 사왔어.",
            "summary": "우유 2개 입고",
            "requires_confirmation": True,
            "actions": [
                {
                    "action_id": "a1",
                    "type": "stock_in",
                    "item": {
                        "raw_name": "우유",
                        "matched_item_id": REQUEST_ID,
                        "matched_name": "우유",
                        "is_new_item": False,
                        "new_item": None,
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
    service = MagicMock(spec=ActionPlanService)
    service.generate = AsyncMock(
        return_value=ActionPlanView(
            request_id=REQUEST_ID,
            plan_id=PLAN_ID,
            payload=payload,
            approved=False,
            executed=False,
            created_at=CREATED_AT,
        )
    )
    app.dependency_overrides[get_action_plan_service] = lambda: service
    app.dependency_overrides[get_inventory_planner_provider] = lambda: MagicMock()

    response = await client.post(f"/api/v1/voice-requests/{REQUEST_ID}/action-plan")

    assert response.status_code == 201
    assert response.json() == {
        "request_id": str(REQUEST_ID),
        "plan_id": str(PLAN_ID),
        "version": "1.0",
        "transcript": "우유 두 개 사왔어.",
        "summary": "우유 2개 입고",
        "requires_confirmation": True,
        "actions": [
            {
                "action_id": "a1",
                "type": "stock_in",
                "item": {
                    "raw_name": "우유",
                    "matched_item_id": str(REQUEST_ID),
                    "matched_name": "우유",
                    "is_new_item": False,
                    "new_item": None,
                },
                "quantity": {
                    "raw_value": 2.0,
                    "raw_unit": "개",
                    "normalized_value": 2.0,
                    "normalized_unit": "개",
                    "conversion_applied": False,
                    "conversion_reason": None,
                },
                "confidence": 0.98,
                "warnings": [],
                "requires_user_input": False,
            }
        ],
        "approved": False,
        "executed": False,
        "created_at": "2026-07-28T12:00:00Z",
    }
    service.generate.assert_awaited_once()
