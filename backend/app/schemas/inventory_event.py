from datetime import datetime
from decimal import Decimal
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field, field_validator

from app.schemas.common import Quantity

InventoryEventType = Literal[
    "stock_in",
    "stock_out",
    "adjustment_in",
    "adjustment_out",
    "initial_stock",
]

# Event types a client may create directly through the manual event API.
# adjustment_in/out and initial_stock are backend-internal only and are produced
# by the target-quantity and correction flows, never by external requests.
ManualEventType = Literal[
    "stock_in",
    "stock_out",
]

# Every event type that can be persisted, including reversals. Used to filter the
# event history, which may contain backend-internal and reversal records.
StoredEventType = Literal[
    "stock_in",
    "stock_out",
    "adjustment_in",
    "adjustment_out",
    "initial_stock",
    "event_reversal",
]

EventSource = Literal[
    "manual",
    "voice",
    "system",
    "correction",
]


class InventoryEventCreate(BaseModel):
    item_id: UUID
    event_type: ManualEventType
    quantity: Decimal = Field(gt=0, max_digits=12, decimal_places=3)
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


class InventoryEventCreateResponse(BaseModel):
    event_id: UUID
    item_id: UUID
    event_type: InventoryEventType
    quantity: Quantity
    signed_quantity: Quantity
    previous_quantity: Quantity
    current_quantity: Quantity
    created_at: datetime


class InventoryEventCorrectionRequest(BaseModel):
    event_type: ManualEventType
    quantity: Decimal = Field(gt=0, max_digits=12, decimal_places=3)
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


class InventoryEventCorrectionResponse(BaseModel):
    original_event_id: UUID
    reversal_event_id: UUID
    replacement_event_id: UUID
    previous_quantity: Quantity
    current_quantity: Quantity
    corrected_at: datetime


class InventoryEventCancellationResponse(BaseModel):
    original_event_id: UUID
    reversal_event_id: UUID
    previous_quantity: Quantity
    current_quantity: Quantity
    cancelled_at: datetime


class InventoryEventListEntry(BaseModel):
    id: UUID
    item_id: UUID
    event_type: str
    quantity: Quantity
    signed_quantity: Quantity
    unit: str
    source: str
    note: str | None
    created_by: UUID | None
    created_at: datetime


class InventoryEventListResponse(BaseModel):
    items: list[InventoryEventListEntry]
    total: int

