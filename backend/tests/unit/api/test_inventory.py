from datetime import UTC, datetime
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock
from uuid import UUID

from fastapi import FastAPI
from httpx import AsyncClient

from app.services.inventory_service import (
    CurrentInventoryListView,
    CurrentInventoryView,
    InventoryDetailView,
    InventoryService,
    InventorySetQuantityView,
    RecentInventoryEventView,
    get_inventory_service,
)

ITEM_ID = UUID("00000000-0000-4000-8000-000000000100")
EVENT_ID = UUID("00000000-0000-4000-8000-000000000102")
UPDATED_AT = datetime(2026, 7, 20, 10, 30, tzinfo=UTC)


def make_inventory_view() -> CurrentInventoryView:
    return CurrentInventoryView(
        item_id=ITEM_ID,
        name="우유",
        quantity=Decimal("2"),
        unit="개",
        category="drink",
        is_active=True,
        updated_at=UPDATED_AT,
    )


async def test_list_current_inventory_returns_front_ready_page(
    app: FastAPI,
    client: AsyncClient,
) -> None:
    service = MagicMock(spec=InventoryService)
    service.list_current_inventory = AsyncMock(
        return_value=CurrentInventoryListView(
            items=[make_inventory_view()],
            total=1,
        )
    )
    app.dependency_overrides[get_inventory_service] = lambda: service

    response = await client.get(
        "/api/v1/inventory",
        params={
            "include_zero": "false",
            "sort": "quantity",
            "order": "asc",
            "limit": 20,
        },
    )

    assert response.status_code == 200
    assert response.json() == {
        "items": [
            {
                "item_id": str(ITEM_ID),
                "name": "우유",
                "quantity": 2.0,
                "unit": "개",
                "category": "drink",
                "is_active": True,
                "updated_at": "2026-07-20T10:30:00Z",
            }
        ],
        "total": 1,
    }
    service.list_current_inventory.assert_awaited_once()


async def test_inventory_detail_returns_snapshot_and_recent_events(
    app: FastAPI,
    client: AsyncClient,
) -> None:
    service = MagicMock(spec=InventoryService)
    service.get_inventory_detail = AsyncMock(
        return_value=InventoryDetailView(
            item=make_inventory_view(),
            recent_events=[
                RecentInventoryEventView(
                    id=EVENT_ID,
                    event_type="stock_in",
                    quantity=Decimal("2"),
                    signed_quantity=Decimal("2"),
                    unit="개",
                    created_at=UPDATED_AT,
                )
            ],
        )
    )
    app.dependency_overrides[get_inventory_service] = lambda: service

    response = await client.get(f"/api/v1/inventory/{ITEM_ID}")

    assert response.status_code == 200
    assert response.json()["quantity"] == 2.0
    assert response.json()["recent_events"] == [
        {
            "id": str(EVENT_ID),
            "event_type": "stock_in",
            "quantity": 2.0,
            "signed_quantity": 2.0,
            "unit": "개",
            "created_at": "2026-07-20T10:30:00Z",
        }
    ]


async def test_inventory_list_rejects_unknown_sort(client: AsyncClient) -> None:
    response = await client.get(
        "/api/v1/inventory",
        params={"sort": "unknown"},
    )

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "VALIDATION_ERROR"


async def test_set_quantity_returns_transition(
    app: FastAPI,
    client: AsyncClient,
) -> None:
    service = MagicMock(spec=InventoryService)
    service.set_inventory_quantity = AsyncMock(
        return_value=InventorySetQuantityView(
            event_id=EVENT_ID,
            item_id=ITEM_ID,
            previous_quantity=Decimal("5"),
            current_quantity=Decimal("2"),
            changed=True,
            created_at=UPDATED_AT,
        )
    )
    app.dependency_overrides[get_inventory_service] = lambda: service

    response = await client.put(
        f"/api/v1/inventory/{ITEM_ID}/quantity",
        json={"quantity": 2, "unit": "개", "note": "실제 수량 확인"},
    )

    assert response.status_code == 200
    assert response.json() == {
        "event_id": str(EVENT_ID),
        "item_id": str(ITEM_ID),
        "previous_quantity": 5.0,
        "current_quantity": 2.0,
        "changed": True,
        "created_at": "2026-07-20T10:30:00Z",
    }
    service.set_inventory_quantity.assert_awaited_once()


async def test_set_quantity_no_change_returns_null_event(
    app: FastAPI,
    client: AsyncClient,
) -> None:
    service = MagicMock(spec=InventoryService)
    service.set_inventory_quantity = AsyncMock(
        return_value=InventorySetQuantityView(
            event_id=None,
            item_id=ITEM_ID,
            previous_quantity=Decimal("2"),
            current_quantity=Decimal("2"),
            changed=False,
            created_at=None,
        )
    )
    app.dependency_overrides[get_inventory_service] = lambda: service

    response = await client.put(
        f"/api/v1/inventory/{ITEM_ID}/quantity",
        json={"quantity": 2, "unit": "개"},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["changed"] is False
    assert body["event_id"] is None
    assert body["created_at"] is None


async def test_set_quantity_rejects_negative_target(client: AsyncClient) -> None:
    response = await client.put(
        f"/api/v1/inventory/{ITEM_ID}/quantity",
        json={"quantity": -1, "unit": "개"},
    )

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "VALIDATION_ERROR"

