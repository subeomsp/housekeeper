from datetime import datetime
from decimal import Decimal
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field, field_validator

from app.schemas.common import Quantity

InventorySort = Literal["updated_at", "name", "quantity"]
SortOrder = Literal["asc", "desc"]


class InventoryListEntry(BaseModel):
    item_id: UUID
    name: str
    quantity: Quantity
    unit: str
    category: str | None
    is_active: bool
    updated_at: datetime


class InventoryListResponse(BaseModel):
    items: list[InventoryListEntry]
    total: int


class RecentInventoryEvent(BaseModel):
    id: UUID
    event_type: str
    quantity: Quantity
    signed_quantity: Quantity
    unit: str
    created_at: datetime


class InventoryDetailResponse(BaseModel):
    item_id: UUID
    name: str
    quantity: Quantity
    unit: str
    category: str | None
    is_active: bool
    updated_at: datetime
    recent_events: list[RecentInventoryEvent]


class InventorySetQuantityRequest(BaseModel):
    quantity: Decimal = Field(ge=0, max_digits=12, decimal_places=3)
    unit: str = Field(min_length=1, max_length=20)
    note: str | None = Field(default=None, max_length=1000)

    @field_validator("unit")
    @classmethod
    def strip_unit(cls, value: str) -> str:
        stripped = value.strip()
        if not stripped:
            raise ValueError("단위는 빈 문자열일 수 없습니다.")
        return stripped

    @field_validator("note")
    @classmethod
    def strip_note(cls, value: str | None) -> str | None:
        if value is None:
            return None
        stripped = value.strip()
        return stripped or None


class InventorySetQuantityResponse(BaseModel):
    event_id: UUID | None
    item_id: UUID
    previous_quantity: Quantity
    current_quantity: Quantity
    changed: bool
    created_at: datetime | None

