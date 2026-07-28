from datetime import datetime
from decimal import Decimal, InvalidOperation
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from app.schemas.common import Quantity


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class ActionPlanWarning(StrictModel):
    code: str = Field(min_length=1, max_length=50)
    message: str = Field(min_length=1, max_length=300)

    @field_validator("code", "message")
    @classmethod
    def strip_text(cls, value: str) -> str:
        stripped = value.strip()
        if not stripped:
            raise ValueError("경고 값은 빈 문자열일 수 없습니다.")
        return stripped


class ActionPlanNewItemDefinition(StrictModel):
    name: str = Field(min_length=1, max_length=100)
    default_unit: str = Field(min_length=1, max_length=20)
    category: str | None = Field(default=None, max_length=50)
    remember_alias: bool = False

    @field_validator("name", "default_unit")
    @classmethod
    def strip_required_text(cls, value: str) -> str:
        stripped = value.strip()
        if not stripped:
            raise ValueError("신규 품목 값은 빈 문자열일 수 없습니다.")
        return stripped

    @field_validator("category")
    @classmethod
    def strip_category(cls, value: str | None) -> str | None:
        if value is None:
            return None
        return value.strip() or None

    @model_validator(mode="after")
    def validate_searchable_name(self) -> "ActionPlanNewItemDefinition":
        if not any(character.isalnum() for character in self.name):
            raise ValueError("품목명에는 문자 또는 숫자가 포함되어야 합니다.")
        return self


class ActionPlanItemReference(StrictModel):
    raw_name: str = Field(min_length=1, max_length=100)
    matched_item_id: UUID | None
    matched_name: str | None = Field(default=None, min_length=1, max_length=100)
    is_new_item: bool
    new_item: ActionPlanNewItemDefinition | None = None

    @field_validator("raw_name", "matched_name")
    @classmethod
    def strip_name(cls, value: str | None) -> str | None:
        if value is None:
            return None
        stripped = value.strip()
        if not stripped:
            raise ValueError("품목명은 빈 문자열일 수 없습니다.")
        return stripped

    @model_validator(mode="after")
    def validate_item_reference(self) -> "ActionPlanItemReference":
        if self.is_new_item:
            if self.matched_item_id is not None or self.matched_name is not None:
                raise ValueError("신규 품목에는 기존 품목 연결 값을 지정할 수 없습니다.")
        else:
            if self.matched_item_id is None or self.matched_name is None:
                raise ValueError("기존 품목에는 품목 ID와 공식 이름이 필요합니다.")
            if self.new_item is not None:
                raise ValueError("기존 품목에는 신규 품목 정의를 지정할 수 없습니다.")
        return self


class ActionPlanQuantity(StrictModel):
    raw_value: float = Field(ge=0, le=999_999_999.999)
    raw_unit: str = Field(min_length=1, max_length=20)
    normalized_value: float | None = Field(
        default=None,
        ge=0,
        le=999_999_999.999,
    )
    normalized_unit: str | None = Field(default=None, min_length=1, max_length=20)
    conversion_applied: bool
    conversion_reason: str | None = Field(default=None, max_length=300)

    @field_validator("raw_unit", "normalized_unit", "conversion_reason")
    @classmethod
    def strip_text(cls, value: str | None) -> str | None:
        if value is None:
            return None
        stripped = value.strip()
        return stripped or None

    @field_validator("raw_value", "normalized_value")
    @classmethod
    def validate_quantity_precision(cls, value: float | None) -> float | None:
        if value is None:
            return None
        try:
            decimal_value = Decimal(str(value))
        except InvalidOperation as exception:
            raise ValueError("수량은 유효한 숫자여야 합니다.") from exception
        exponent = decimal_value.as_tuple().exponent
        if isinstance(exponent, int) and exponent < -3:
            raise ValueError("수량은 소수점 셋째 자리까지만 허용합니다.")
        return value

    @model_validator(mode="after")
    def validate_normalized_quantity_pair(self) -> "ActionPlanQuantity":
        if (self.normalized_value is None) != (self.normalized_unit is None):
            raise ValueError("정규화 수량과 단위는 함께 지정하거나 함께 비워야 합니다.")
        if self.conversion_applied:
            if self.normalized_value is None or self.conversion_reason is None:
                raise ValueError("단위 변환에는 결과 수량과 변환 근거가 필요합니다.")
        elif self.conversion_reason is not None:
            raise ValueError("단위 변환을 하지 않았다면 변환 근거를 지정할 수 없습니다.")
        return self


class ActionPlanAction(StrictModel):
    action_id: str = Field(min_length=1, max_length=50)
    type: Literal["stock_in", "stock_out", "set_quantity"]
    item: ActionPlanItemReference
    quantity: ActionPlanQuantity
    confidence: float = Field(ge=0, le=1)
    warnings: list[ActionPlanWarning] = Field(max_length=20)
    requires_user_input: bool

    @field_validator("action_id")
    @classmethod
    def strip_action_id(cls, value: str) -> str:
        stripped = value.strip()
        if not stripped:
            raise ValueError("Action ID는 빈 문자열일 수 없습니다.")
        return stripped

    @model_validator(mode="after")
    def validate_quantity_for_action_type(self) -> "ActionPlanAction":
        if self.type in {"stock_in", "stock_out"}:
            if self.quantity.raw_value <= 0:
                raise ValueError("입고와 소비 수량은 0보다 커야 합니다.")
            if self.quantity.normalized_value is not None and self.quantity.normalized_value <= 0:
                raise ValueError("입고와 소비의 정규화 수량은 0보다 커야 합니다.")
        return self


class ActionPlanPayload(StrictModel):
    version: Literal["1.0"]
    transcript: str = Field(min_length=1)
    summary: str = Field(min_length=1, max_length=500)
    requires_confirmation: Literal[True]
    actions: list[ActionPlanAction] = Field(min_length=1, max_length=50)

    @field_validator("transcript", "summary")
    @classmethod
    def strip_text(cls, value: str) -> str:
        stripped = value.strip()
        if not stripped:
            raise ValueError("Action Plan 텍스트는 빈 문자열일 수 없습니다.")
        return stripped

    @model_validator(mode="after")
    def validate_unique_action_ids(self) -> "ActionPlanPayload":
        action_ids = [action.action_id for action in self.actions]
        if len(action_ids) != len(set(action_ids)):
            raise ValueError("Action ID는 Plan 안에서 중복될 수 없습니다.")
        return self


class ActionPlanResponse(BaseModel):
    request_id: UUID
    plan_id: UUID
    version: Literal["1.0"]
    transcript: str
    summary: str
    requires_confirmation: Literal[True]
    actions: list[ActionPlanAction]
    approved: bool
    executed: bool
    created_at: datetime


class ActionPlanExecutionResponse(BaseModel):
    success: Literal[True] = True
    inventory_updated: bool
    event_count: int = Field(ge=0)
    already_executed: bool


class ActionPlanActionUpdate(BaseModel):
    type: Literal["stock_in", "stock_out", "set_quantity"]
    item_id: UUID
    quantity: float = Field(ge=0, le=999_999_999.999)
    unit: str = Field(min_length=1, max_length=20)
    remember_alias: bool = False

    @field_validator("quantity")
    @classmethod
    def validate_quantity_precision(cls, value: float) -> float:
        return ActionPlanQuantity.validate_quantity_precision(value) or 0

    @field_validator("unit")
    @classmethod
    def strip_unit(cls, value: str) -> str:
        stripped = value.strip()
        if not stripped:
            raise ValueError("단위는 빈 문자열일 수 없습니다.")
        return stripped

    @model_validator(mode="after")
    def validate_quantity_for_action_type(self) -> "ActionPlanActionUpdate":
        if self.type in {"stock_in", "stock_out"} and self.quantity <= 0:
            raise ValueError("입고와 소비 수량은 0보다 커야 합니다.")
        return self


class ActionPlanNewItemUpdate(BaseModel):
    type: Literal["stock_in", "stock_out", "set_quantity"]
    name: str = Field(min_length=1, max_length=100)
    default_unit: str = Field(min_length=1, max_length=20)
    category: str | None = Field(default=None, max_length=50)
    quantity: float = Field(ge=0, le=999_999_999.999)
    remember_alias: bool = False

    @field_validator("quantity")
    @classmethod
    def validate_quantity_precision(cls, value: float) -> float:
        return ActionPlanQuantity.validate_quantity_precision(value) or 0

    @field_validator("name", "default_unit")
    @classmethod
    def strip_required_text(cls, value: str) -> str:
        stripped = value.strip()
        if not stripped:
            raise ValueError("신규 품목 값은 빈 문자열일 수 없습니다.")
        return stripped

    @field_validator("category")
    @classmethod
    def strip_category(cls, value: str | None) -> str | None:
        if value is None:
            return None
        return value.strip() or None

    @model_validator(mode="after")
    def validate_new_item(self) -> "ActionPlanNewItemUpdate":
        if not any(character.isalnum() for character in self.name):
            raise ValueError("품목명에는 문자 또는 숫자가 포함되어야 합니다.")
        if self.type in {"stock_in", "stock_out"} and self.quantity <= 0:
            raise ValueError("입고와 소비 수량은 0보다 커야 합니다.")
        return self


class PlannerInventoryItem(BaseModel):
    item_id: UUID
    name: str
    default_unit: str
    current_quantity: Quantity
    aliases: list[str] = Field(default_factory=list)
