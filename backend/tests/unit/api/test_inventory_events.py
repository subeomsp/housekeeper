from datetime import UTC, datetime
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock
from uuid import UUID

from fastapi import FastAPI
from httpx import AsyncClient

from app.services.inventory_service import (
    InventoryEventCancellationView,
    InventoryEventCorrectionView,
    InventoryEventCreateView,
    InventoryEventListEntryView,
    InventoryEventListView,
    InventoryService,
    get_inventory_service,
)

ITEM_ID = UUID("00000000-0000-4000-8000-000000000100")
EVENT_ID = UUID("00000000-0000-4000-8000-000000000102")
CREATED_AT = datetime(2026, 7, 20, 10, 30, tzinfo=UTC)


async def test_create_inventory_event_returns_quantity_transition(
    app: FastAPI,
    client: AsyncClient,
) -> None:
    service = MagicMock(spec=InventoryService)
    service.create_inventory_event = AsyncMock(
        return_value=InventoryEventCreateView(
            event_id=EVENT_ID,
            item_id=ITEM_ID,
            event_type="stock_in",
            quantity=Decimal("2"),
            signed_quantity=Decimal("2"),
            previous_quantity=Decimal("0"),
            current_quantity=Decimal("2"),
            created_at=CREATED_AT,
        )
    )
    app.dependency_overrides[get_inventory_service] = lambda: service

    response = await client.post(
        "/api/v1/inventory-events",
        json={
            "item_id": str(ITEM_ID),
            "event_type": "stock_in",
            "quantity": 2,
            "unit": "개",
            "note": "장보기",
        },
    )

    assert response.status_code == 201
    assert response.json() == {
        "event_id": str(EVENT_ID),
        "item_id": str(ITEM_ID),
        "event_type": "stock_in",
        "quantity": 2.0,
        "signed_quantity": 2.0,
        "previous_quantity": 0.0,
        "current_quantity": 2.0,
        "created_at": "2026-07-20T10:30:00Z",
    }
    service.create_inventory_event.assert_awaited_once()


async def test_create_inventory_event_rejects_nonpositive_quantity(
    client: AsyncClient,
) -> None:
    response = await client.post(
        "/api/v1/inventory-events",
        json={
            "item_id": str(ITEM_ID),
            "event_type": "stock_in",
            "quantity": 0,
            "unit": "개",
        },
    )

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "VALIDATION_ERROR"


async def test_create_inventory_event_rejects_client_reversal(
    client: AsyncClient,
) -> None:
    response = await client.post(
        "/api/v1/inventory-events",
        json={
            "item_id": str(ITEM_ID),
            "event_type": "event_reversal",
            "quantity": 1,
            "unit": "개",
        },
    )

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "VALIDATION_ERROR"


async def test_create_inventory_event_rejects_adjustment_type(
    client: AsyncClient,
) -> None:
    response = await client.post(
        "/api/v1/inventory-events",
        json={
            "item_id": str(ITEM_ID),
            "event_type": "adjustment_in",
            "quantity": 1,
            "unit": "개",
        },
    )

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "VALIDATION_ERROR"


async def test_list_inventory_events_returns_history_and_forwards_filters(
    app: FastAPI,
    client: AsyncClient,
) -> None:
    service = MagicMock(spec=InventoryService)
    service.list_inventory_events = AsyncMock(
        return_value=InventoryEventListView(
            items=[
                InventoryEventListEntryView(
                    id=EVENT_ID,
                    item_id=ITEM_ID,
                    event_type="stock_in",
                    quantity=Decimal("2"),
                    signed_quantity=Decimal("2"),
                    unit="개",
                    source="manual",
                    note="장보기",
                    created_by=None,
                    created_at=CREATED_AT,
                )
            ],
            total=1,
        )
    )
    app.dependency_overrides[get_inventory_service] = lambda: service

    response = await client.get(
        "/api/v1/inventory-events",
        params={
            "item_id": str(ITEM_ID),
            "event_type": "stock_in",
            "source": "manual",
            "from": "2026-07-01T00:00:00Z",
            "to": "2026-07-20T00:00:00Z",
            "limit": 20,
        },
    )

    assert response.status_code == 200
    assert response.json() == {
        "items": [
            {
                "id": str(EVENT_ID),
                "item_id": str(ITEM_ID),
                "event_type": "stock_in",
                "quantity": 2.0,
                "signed_quantity": 2.0,
                "unit": "개",
                "source": "manual",
                "note": "장보기",
                "created_by": None,
                "created_at": "2026-07-20T10:30:00Z",
            }
        ],
        "total": 1,
    }
    service.list_inventory_events.assert_awaited_once()
    kwargs = service.list_inventory_events.await_args.kwargs
    assert kwargs["item_id"] == ITEM_ID
    assert kwargs["event_type"] == "stock_in"
    assert kwargs["source"] == "manual"
    assert kwargs["created_from"] == datetime(2026, 7, 1, tzinfo=UTC)
    assert kwargs["created_to"] == datetime(2026, 7, 20, tzinfo=UTC)
    assert kwargs["limit"] == 20


async def test_list_inventory_events_rejects_unknown_event_type(
    client: AsyncClient,
) -> None:
    response = await client.get(
        "/api/v1/inventory-events",
        params={"event_type": "unknown"},
    )

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "VALIDATION_ERROR"


REVERSAL_ID = UUID("00000000-0000-4000-8000-000000000201")
REPLACEMENT_ID = UUID("00000000-0000-4000-8000-000000000202")


async def test_correct_inventory_event_returns_transition(
    app: FastAPI,
    client: AsyncClient,
) -> None:
    service = MagicMock(spec=InventoryService)
    service.correct_inventory_event = AsyncMock(
        return_value=InventoryEventCorrectionView(
            original_event_id=EVENT_ID,
            reversal_event_id=REVERSAL_ID,
            replacement_event_id=REPLACEMENT_ID,
            previous_quantity=Decimal("20"),
            current_quantity=Decimal("2"),
            corrected_at=CREATED_AT,
        )
    )
    app.dependency_overrides[get_inventory_service] = lambda: service

    response = await client.patch(
        f"/api/v1/inventory-events/{EVENT_ID}",
        json={
            "event_type": "stock_in",
            "quantity": 2,
            "unit": "개",
            "note": "20개가 아니라 2개",
        },
    )

    assert response.status_code == 200
    assert response.json() == {
        "original_event_id": str(EVENT_ID),
        "reversal_event_id": str(REVERSAL_ID),
        "replacement_event_id": str(REPLACEMENT_ID),
        "previous_quantity": 20.0,
        "current_quantity": 2.0,
        "corrected_at": "2026-07-20T10:30:00Z",
    }
    service.correct_inventory_event.assert_awaited_once()


async def test_correct_inventory_event_rejects_adjustment_type(
    client: AsyncClient,
) -> None:
    response = await client.patch(
        f"/api/v1/inventory-events/{EVENT_ID}",
        json={"event_type": "adjustment_in", "quantity": 2, "unit": "개"},
    )

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "VALIDATION_ERROR"


async def test_cancel_inventory_event_returns_transition(
    app: FastAPI,
    client: AsyncClient,
) -> None:
    service = MagicMock(spec=InventoryService)
    service.cancel_inventory_event = AsyncMock(
        return_value=InventoryEventCancellationView(
            original_event_id=EVENT_ID,
            reversal_event_id=REVERSAL_ID,
            previous_quantity=Decimal("2"),
            current_quantity=Decimal("0"),
            cancelled_at=CREATED_AT,
        )
    )
    app.dependency_overrides[get_inventory_service] = lambda: service

    response = await client.delete(f"/api/v1/inventory-events/{EVENT_ID}")

    assert response.status_code == 200
    assert response.json() == {
        "original_event_id": str(EVENT_ID),
        "reversal_event_id": str(REVERSAL_ID),
        "previous_quantity": 2.0,
        "current_quantity": 0.0,
        "cancelled_at": "2026-07-20T10:30:00Z",
    }
    service.cancel_inventory_event.assert_awaited_once()

