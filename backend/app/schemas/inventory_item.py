from datetime import datetime
from typing import Self
from uuid import UUID

from pydantic import BaseModel, Field, field_validator, model_validator

from app.schemas.common import Quantity


class InventoryItemCreate(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    default_unit: str = Field(min_length=1, max_length=20)
    category: str | None = Field(default=None, max_length=50)

    @field_validator("name", "default_unit")
    @classmethod
    def strip_required_text(cls, value: str) -> str:
        stripped = value.strip()
        if not stripped:
            raise ValueError("빈 문자열일 수 없습니다.")
        return stripped

    @field_validator("category")
    @classmethod
    def strip_optional_text(cls, value: str | None) -> str | None:
        if value is None:
            return None
        stripped = value.strip()
        return stripped or None

    @model_validator(mode="after")
    def validate_searchable_name(self) -> Self:
        if not any(character.isalnum() for character in self.name):
            raise ValueError("품목명에는 문자 또는 숫자가 포함되어야 합니다.")
        return self


class InventoryItemUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=100)
    default_unit: str | None = Field(default=None, min_length=1, max_length=20)
    category: str | None = Field(default=None, max_length=50)

    @field_validator("name", "default_unit")
    @classmethod
    def strip_optional_required_text(cls, value: str | None) -> str | None:
        if value is None:
            return None
        stripped = value.strip()
        if not stripped:
            raise ValueError("빈 문자열일 수 없습니다.")
        return stripped

    @field_validator("category")
    @classmethod
    def strip_update_category(cls, value: str | None) -> str | None:
        if value is None:
            return None
        stripped = value.strip()
        return stripped or None

    @model_validator(mode="after")
    def validate_update(self) -> Self:
        if not self.model_fields_set:
            raise ValueError("하나 이상의 수정 값을 입력해야 합니다.")
        if "name" in self.model_fields_set and self.name is None:
            raise ValueError("품목명은 null일 수 없습니다.")
        if "default_unit" in self.model_fields_set and self.default_unit is None:
            raise ValueError("기본 단위는 null일 수 없습니다.")
        if self.name is not None and not any(
            character.isalnum() for character in self.name
        ):
            raise ValueError("품목명에는 문자 또는 숫자가 포함되어야 합니다.")
        return self


class InventoryItemResponse(BaseModel):
    id: UUID
    name: str
    default_unit: str
    category: str | None
    is_active: bool
    current_quantity: Quantity
    created_at: datetime


class InventoryItemListEntry(BaseModel):
    id: UUID
    name: str
    default_unit: str
    category: str | None
    is_active: bool
    current_quantity: Quantity


class InventoryItemListResponse(BaseModel):
    items: list[InventoryItemListEntry]
    total: int


class InventoryItemMutationResponse(BaseModel):
    id: UUID
    name: str
    default_unit: str
    category: str | None
    is_active: bool
    current_quantity: Quantity
    updated_at: datetime
