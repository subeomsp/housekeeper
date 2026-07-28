from uuid import UUID

import pytest
from pydantic import ValidationError

from app.schemas.action_plan import ActionPlanPayload

ITEM_ID = UUID("00000000-0000-4000-8000-000000000111")


def valid_payload() -> dict[str, object]:
    return {
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
                    "matched_item_id": str(ITEM_ID),
                    "matched_name": "우유",
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


def test_action_plan_schema_accepts_strict_valid_payload() -> None:
    payload = ActionPlanPayload.model_validate(valid_payload())

    assert payload.version == "1.0"
    assert payload.requires_confirmation is True
    assert payload.actions[0].quantity.normalized_value == 2


@pytest.mark.parametrize(
    ("path", "value"),
    [
        (("version",), "2.0"),
        (("requires_confirmation",), False),
        (("actions", 0, "type"), "adjustment_in"),
        (("actions", 0, "quantity", "raw_value"), 1.2345),
    ],
)
def test_action_plan_schema_rejects_unsupported_values(
    path: tuple[str | int, ...],
    value: object,
) -> None:
    payload = valid_payload()
    target: object = payload
    for key in path[:-1]:
        target = target[key]  # type: ignore[index]
    target[path[-1]] = value  # type: ignore[index]

    with pytest.raises(ValidationError):
        ActionPlanPayload.model_validate(payload)


def test_action_plan_schema_rejects_duplicate_action_ids_and_extra_fields() -> None:
    payload = valid_payload()
    first_action = payload["actions"][0]  # type: ignore[index]
    payload["actions"] = [first_action, first_action]
    first_action["unexpected"] = True

    with pytest.raises(ValidationError):
        ActionPlanPayload.model_validate(payload)


def test_set_quantity_allows_zero_but_stock_change_does_not() -> None:
    payload = valid_payload()
    action = payload["actions"][0]  # type: ignore[index]
    action["type"] = "set_quantity"
    action["quantity"]["raw_value"] = 0
    action["quantity"]["normalized_value"] = 0

    parsed = ActionPlanPayload.model_validate(payload)
    assert parsed.actions[0].quantity.normalized_value == 0

    action["type"] = "stock_out"
    with pytest.raises(ValidationError):
        ActionPlanPayload.model_validate(payload)
