from decimal import Decimal
from uuid import UUID

from app.models import InventoryItem
from app.repositories.inventory_item_repository import PlannerInventoryRecord
from app.schemas.action_plan import ActionPlanPayload
from app.services.action_plan_service import ActionPlanValidator

HOUSEHOLD_ID = UUID("00000000-0000-4000-8000-000000000099")
ITEM_ID = UUID("00000000-0000-4000-8000-000000000111")


def inventory_record(quantity: str = "5") -> PlannerInventoryRecord:
    return PlannerInventoryRecord(
        item=InventoryItem(
            id=ITEM_ID,
            household_id=HOUSEHOLD_ID,
            name="우유",
            normalized_name="우유",
            default_unit="개",
            is_active=True,
        ),
        current_quantity=Decimal(quantity),
    )


def action_plan(
    *,
    event_type: str = "stock_out",
    quantity: float = 2,
    unit: str = "개",
    normalized_quantity: float | None = 2,
    normalized_unit: str | None = "개",
    confidence: float = 0.98,
    requires_user_input: bool = False,
    item_id: UUID | None = ITEM_ID,
    matched_name: str | None = "우유",
    is_new_item: bool = False,
) -> ActionPlanPayload:
    return ActionPlanPayload.model_validate(
        {
            "version": "1.0",
            "transcript": "우유 두 개 마셨어.",
            "summary": "우유 2개 소비",
            "requires_confirmation": True,
            "actions": [
                {
                    "action_id": "a1",
                    "type": event_type,
                    "item": {
                        "raw_name": "우유",
                        "matched_item_id": item_id,
                        "matched_name": matched_name,
                        "is_new_item": is_new_item,
                    },
                    "quantity": {
                        "raw_value": quantity,
                        "raw_unit": unit,
                        "normalized_value": normalized_quantity,
                        "normalized_unit": normalized_unit,
                        "conversion_applied": False,
                        "conversion_reason": None,
                    },
                    "confidence": confidence,
                    "warnings": [],
                    "requires_user_input": requires_user_input,
                }
            ],
        }
    )


def issue_codes(payload: ActionPlanPayload, quantity: str = "5") -> set[str]:
    issues = ActionPlanValidator().validate(
        payload=payload,
        transcript="우유 두 개 마셨어.",
        inventory_records=[inventory_record(quantity)],
    )
    return {issue.code for issue in issues}


def test_validator_accepts_household_item_and_non_negative_result() -> None:
    assert issue_codes(action_plan()) == set()


def test_validator_rejects_negative_inventory_at_plan_time() -> None:
    assert "INSUFFICIENT_INVENTORY" in issue_codes(action_plan(quantity=6, normalized_quantity=6))


def test_validator_requires_confirmation_for_unknown_unit() -> None:
    payload = action_plan(
        unit="박스",
        normalized_quantity=None,
        normalized_unit=None,
        requires_user_input=True,
    )

    assert issue_codes(payload) == set()


def test_validator_rejects_foreign_item_and_low_confidence_without_input() -> None:
    payload = action_plan(
        item_id=UUID("00000000-0000-4000-8000-000000000222"),
        confidence=0.5,
    )

    assert issue_codes(payload) == {
        "LOW_CONFIDENCE_REQUIRES_INPUT",
        "MATCHED_ITEM_INVALID",
    }


def test_validator_allows_unmatched_new_item_only_with_user_input() -> None:
    payload = action_plan(
        item_id=None,
        matched_name=None,
        is_new_item=True,
        requires_user_input=True,
    )

    assert issue_codes(payload) == set()


def test_validator_accepts_set_quantity_zero_without_negative_delta() -> None:
    payload = action_plan(
        event_type="set_quantity",
        quantity=0,
        normalized_quantity=0,
    )

    assert issue_codes(payload, quantity="1") == set()
