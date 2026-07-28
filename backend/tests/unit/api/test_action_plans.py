from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock
from uuid import UUID

from fastapi import FastAPI
from httpx import AsyncClient

from app.schemas.action_plan import ActionPlanPayload
from app.services.action_plan_service import (
    ActionPlanService,
    ActionPlanView,
    get_action_plan_service,
)

REQUEST_ID = UUID("00000000-0000-4000-8000-000000000501")
PLAN_ID = UUID("00000000-0000-4000-8000-000000000601")
ITEM_ID = UUID("00000000-0000-4000-8000-000000000111")
CREATED_AT = datetime(2026, 7, 28, 14, 0, tzinfo=UTC)


def plan_view(*, action_count: int = 1) -> ActionPlanView:
    actions = [
        {
            "action_id": f"a{index + 1}",
            "type": "stock_in",
            "item": {
                "raw_name": "우유",
                "matched_item_id": ITEM_ID,
                "matched_name": "우유",
                "is_new_item": False,
            },
            "quantity": {
                "raw_value": index + 1,
                "raw_unit": "개",
                "normalized_value": index + 1,
                "normalized_unit": "개",
                "conversion_applied": False,
                "conversion_reason": None,
            },
            "confidence": 0.98,
            "warnings": [],
            "requires_user_input": False,
        }
        for index in range(action_count)
    ]
    return ActionPlanView(
        request_id=REQUEST_ID,
        plan_id=PLAN_ID,
        payload=ActionPlanPayload.model_validate(
            {
                "version": "1.0",
                "transcript": "우유 사왔어.",
                "summary": "우유 입고",
                "requires_confirmation": True,
                "actions": actions,
            }
        ),
        approved=False,
        executed=False,
        created_at=CREATED_AT,
    )


async def test_get_action_plan_returns_saved_plan(
    app: FastAPI,
    client: AsyncClient,
) -> None:
    service = MagicMock(spec=ActionPlanService)
    service.get = AsyncMock(return_value=plan_view())
    app.dependency_overrides[get_action_plan_service] = lambda: service

    response = await client.get(f"/api/v1/action-plan/{REQUEST_ID}")

    assert response.status_code == 200
    assert response.json()["request_id"] == str(REQUEST_ID)
    assert response.json()["actions"][0]["action_id"] == "a1"
    service.get.assert_awaited_once()


async def test_patch_action_forwards_user_confirmed_values(
    app: FastAPI,
    client: AsyncClient,
) -> None:
    service = MagicMock(spec=ActionPlanService)
    service.update_action = AsyncMock(return_value=plan_view())
    app.dependency_overrides[get_action_plan_service] = lambda: service

    response = await client.patch(
        f"/api/v1/action-plan/{REQUEST_ID}/actions/a1",
        json={
            "type": "set_quantity",
            "item_id": str(ITEM_ID),
            "quantity": 0,
            "unit": "개",
        },
    )

    assert response.status_code == 200
    call = service.update_action.await_args.kwargs
    assert call["action_id"] == "a1"
    assert call["data"].type == "set_quantity"
    assert call["data"].quantity == 0


async def test_delete_action_returns_remaining_plan(
    app: FastAPI,
    client: AsyncClient,
) -> None:
    service = MagicMock(spec=ActionPlanService)
    service.delete_action = AsyncMock(return_value=plan_view())
    app.dependency_overrides[get_action_plan_service] = lambda: service

    response = await client.delete(f"/api/v1/action-plan/{REQUEST_ID}/actions/a2")

    assert response.status_code == 200
    service.delete_action.assert_awaited_once()


async def test_stock_change_rejects_zero_quantity(client: AsyncClient) -> None:
    response = await client.patch(
        f"/api/v1/action-plan/{REQUEST_ID}/actions/a1",
        json={
            "type": "stock_out",
            "item_id": str(ITEM_ID),
            "quantity": 0,
            "unit": "개",
        },
    )

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "VALIDATION_ERROR"
