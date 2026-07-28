from typing import Any


class AppError(Exception):
    def __init__(
        self,
        *,
        code: str,
        message: str,
        status_code: int,
        details: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.status_code = status_code
        self.details = details or {}


def duplicate_item_name_error(name: str) -> AppError:
    return AppError(
        code="DUPLICATE_ITEM_NAME",
        message="같은 이름의 품목이 이미 존재합니다.",
        status_code=409,
        details={"name": name},
    )


def item_not_found_error(item_id: str) -> AppError:
    return AppError(
        code="ITEM_NOT_FOUND",
        message="품목을 찾을 수 없습니다.",
        status_code=404,
        details={"item_id": item_id},
    )


def household_access_denied_error(item_id: str) -> AppError:
    return AppError(
        code="HOUSEHOLD_ACCESS_DENIED",
        message="다른 Household의 품목에는 접근할 수 없습니다.",
        status_code=403,
        details={"item_id": item_id},
    )


def item_has_inventory_error(item_id: str, current_quantity: str) -> AppError:
    return AppError(
        code="ITEM_HAS_INVENTORY",
        message="현재 수량이 남아 있는 품목은 보관할 수 없습니다.",
        status_code=409,
        details={
            "item_id": item_id,
            "current_quantity": current_quantity,
        },
    )


def unit_change_requires_zero_inventory_error(
    item_id: str,
    current_quantity: str,
) -> AppError:
    return AppError(
        code="UNIT_CHANGE_REQUIRES_ZERO_INVENTORY",
        message="현재 수량이 0일 때만 기본 단위를 변경할 수 있습니다.",
        status_code=409,
        details={
            "item_id": item_id,
            "current_quantity": current_quantity,
        },
    )


def unit_mismatch_error(
    item_id: str,
    expected_unit: str,
    requested_unit: str,
) -> AppError:
    return AppError(
        code="UNIT_MISMATCH",
        message="Event 단위는 품목의 기본 단위와 같아야 합니다.",
        status_code=422,
        details={
            "item_id": item_id,
            "expected_unit": expected_unit,
            "requested_unit": requested_unit,
        },
    )


def inactive_item_error(item_id: str) -> AppError:
    return AppError(
        code="INACTIVE_ITEM",
        message="보관된 품목에는 재고 Event를 생성할 수 없습니다.",
        status_code=409,
        details={"item_id": item_id},
    )


def insufficient_inventory_error(
    item_id: str,
    current_quantity: str,
    requested_quantity: str,
) -> AppError:
    return AppError(
        code="INSUFFICIENT_INVENTORY",
        message="현재 재고보다 많은 수량을 소비할 수 없습니다.",
        status_code=409,
        details={
            "item_id": item_id,
            "current_quantity": current_quantity,
            "requested_quantity": requested_quantity,
        },
    )


def event_not_found_error(event_id: str) -> AppError:
    return AppError(
        code="EVENT_NOT_FOUND",
        message="재고 Event를 찾을 수 없습니다.",
        status_code=404,
        details={"event_id": event_id},
    )


def event_already_reversed_error(event_id: str) -> AppError:
    return AppError(
        code="EVENT_ALREADY_REVERSED",
        message="이미 취소된 Event는 다시 정정하거나 취소할 수 없습니다.",
        status_code=409,
        details={"event_id": event_id},
    )


def event_not_correctable_error(event_id: str) -> AppError:
    return AppError(
        code="EVENT_NOT_CORRECTABLE",
        message="Reversal Event는 정정하거나 취소할 수 없습니다.",
        status_code=409,
        details={"event_id": event_id},
    )


def voice_request_not_found_error(request_id: str) -> AppError:
    return AppError(
        code="VOICE_REQUEST_NOT_FOUND",
        message="음성 요청을 찾을 수 없습니다.",
        status_code=404,
        details={"request_id": request_id},
    )


def voice_request_not_plannable_error(request_id: str, status: str) -> AppError:
    return AppError(
        code="VOICE_REQUEST_NOT_PLANNABLE",
        message="현재 상태에서는 Action Plan을 생성할 수 없습니다.",
        status_code=409,
        details={"request_id": request_id, "status": status},
    )


def planner_not_configured_error() -> AppError:
    return AppError(
        code="PLANNER_NOT_CONFIGURED",
        message="Action Plan 생성 Provider가 설정되지 않았습니다.",
        status_code=503,
    )


def action_plan_provider_error() -> AppError:
    return AppError(
        code="ACTION_PLAN_PROVIDER_ERROR",
        message="Action Plan을 생성하지 못했습니다. 잠시 후 다시 시도해 주세요.",
        status_code=502,
    )


def action_plan_invalid_error(issues: list[dict[str, str]]) -> AppError:
    return AppError(
        code="ACTION_PLAN_INVALID",
        message="생성된 Action Plan이 실행 안전성 검증을 통과하지 못했습니다.",
        status_code=422,
        details={"issues": issues},
    )


def action_plan_not_found_error(request_id: str) -> AppError:
    return AppError(
        code="ACTION_PLAN_NOT_FOUND",
        message="Action Plan을 찾을 수 없습니다.",
        status_code=404,
        details={"request_id": request_id},
    )


def action_plan_not_editable_error(request_id: str) -> AppError:
    return AppError(
        code="ACTION_PLAN_NOT_EDITABLE",
        message="대기 중인 Action Plan만 수정할 수 있습니다.",
        status_code=409,
        details={"request_id": request_id},
    )


def action_plan_action_not_found_error(request_id: str, action_id: str) -> AppError:
    return AppError(
        code="ACTION_PLAN_ACTION_NOT_FOUND",
        message="Action Plan에서 해당 Action을 찾을 수 없습니다.",
        status_code=404,
        details={"request_id": request_id, "action_id": action_id},
    )


def action_plan_requires_action_error(request_id: str) -> AppError:
    return AppError(
        code="ACTION_PLAN_REQUIRES_ACTION",
        message="마지막 Action은 삭제할 수 없습니다. 전체 취소를 사용해 주세요.",
        status_code=409,
        details={"request_id": request_id},
    )


def item_alias_conflict_error(alias: str, item_id: str) -> AppError:
    return AppError(
        code="ITEM_ALIAS_CONFLICT",
        message="이 음성 표현은 이미 다른 품목에 연결되어 있습니다.",
        status_code=409,
        details={"alias": alias, "existing_item_id": item_id},
    )
