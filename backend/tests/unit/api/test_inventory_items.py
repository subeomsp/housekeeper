from datetime import UTC, datetime
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock
from uuid import UUID

from fastapi import FastAPI
from httpx import AsyncClient

from app.core.exceptions import duplicate_item_name_error
from app.services.inventory_item_service import (
    InventoryItemListView,
    InventoryItemService,
    InventoryItemView,
    get_inventory_item_service,
)

ITEM_ID = UUID("00000000-0000-4000-8000-000000000100")
CREATED_AT = datetime(2026, 7, 20, 10, 0, tzinfo=UTC)


def make_item_view() -> InventoryItemView:
    return InventoryItemView(
        id=ITEM_ID,
        name="우유",
        default_unit="개",
        category="drink",
        is_active=True,
        current_quantity=Decimal("0"),
        created_at=CREATED_AT,
        updated_at=CREATED_AT,
    )


async def test_create_inventory_item_returns_created_item(
    app: FastAPI,
    client: AsyncClient,
) -> None:
    service = MagicMock(spec=InventoryItemService)
    service.create_item = AsyncMock(return_value=make_item_view())
    app.dependency_overrides[get_inventory_item_service] = lambda: service

    response = await client.post(
        "/api/v1/inventory-items",
        json={"name": "우유", "default_unit": "개", "category": "drink"},
    )

    assert response.status_code == 201
    assert response.json() == {
        "id": str(ITEM_ID),
        "name": "우유",
        "default_unit": "개",
        "category": "drink",
        "is_active": True,
        "current_quantity": 0.0,
        "created_at": "2026-07-20T10:00:00Z",
    }
    service.create_item.assert_awaited_once()


async def test_create_inventory_item_returns_common_duplicate_error(
    app: FastAPI,
    client: AsyncClient,
) -> None:
    service = MagicMock(spec=InventoryItemService)
    service.create_item = AsyncMock(side_effect=duplicate_item_name_error("우유"))
    app.dependency_overrides[get_inventory_item_service] = lambda: service

    response = await client.post(
        "/api/v1/inventory-items",
        json={"name": "우유", "default_unit": "개"},
    )

    assert response.status_code == 409
    assert response.json() == {
        "error": {
            "code": "DUPLICATE_ITEM_NAME",
            "message": "같은 이름의 품목이 이미 존재합니다.",
            "details": {"name": "우유"},
        }
    }


async def test_create_inventory_item_returns_common_validation_error(
    client: AsyncClient,
) -> None:
    response = await client.post(
        "/api/v1/inventory-items",
        json={"name": "   ", "default_unit": "개"},
    )

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "VALIDATION_ERROR"


async def test_list_inventory_items_returns_page(
    app: FastAPI,
    client: AsyncClient,
) -> None:
    service = MagicMock(spec=InventoryItemService)
    service.list_items = AsyncMock(
        return_value=InventoryItemListView(items=[make_item_view()], total=1)
    )
    app.dependency_overrides[get_inventory_item_service] = lambda: service

    response = await client.get(
        "/api/v1/inventory-items",
        params={"search": "우유", "include_inactive": "true", "limit": 20},
    )

    assert response.status_code == 200
    assert response.json()["total"] == 1
    assert response.json()["items"][0]["current_quantity"] == 0.0
    service.list_items.assert_awaited_once()


async def test_update_inventory_item_returns_updated_state(
    app: FastAPI,
    client: AsyncClient,
) -> None:
    item = make_item_view()
    updated = InventoryItemView(
        id=item.id,
        name="저지방 우유",
        default_unit=item.default_unit,
        category=None,
        is_active=True,
        current_quantity=item.current_quantity,
        created_at=item.created_at,
        updated_at=item.updated_at,
    )
    service = MagicMock(spec=InventoryItemService)
    service.update_item = AsyncMock(return_value=updated)
    app.dependency_overrides[get_inventory_item_service] = lambda: service

    response = await client.patch(
        f"/api/v1/inventory-items/{ITEM_ID}",
        json={"name": "저지방 우유", "category": None},
    )

    assert response.status_code == 200
    assert response.json()["name"] == "저지방 우유"
    assert response.json()["category"] is None


async def test_archive_inventory_item_returns_inactive_state(
    app: FastAPI,
    client: AsyncClient,
) -> None:
    item = make_item_view()
    archived = InventoryItemView(
        id=item.id,
        name=item.name,
        default_unit=item.default_unit,
        category=item.category,
        is_active=False,
        current_quantity=item.current_quantity,
        created_at=item.created_at,
        updated_at=item.updated_at,
    )
    service = MagicMock(spec=InventoryItemService)
    service.archive_item = AsyncMock(return_value=archived)
    app.dependency_overrides[get_inventory_item_service] = lambda: service

    response = await client.delete(f"/api/v1/inventory-items/{ITEM_ID}")

    assert response.status_code == 200
    assert response.json()["is_active"] is False


async def test_restore_inventory_item_returns_active_state(
    app: FastAPI,
    client: AsyncClient,
) -> None:
    service = MagicMock(spec=InventoryItemService)
    service.restore_item = AsyncMock(return_value=make_item_view())
    app.dependency_overrides[get_inventory_item_service] = lambda: service

    response = await client.post(f"/api/v1/inventory-items/{ITEM_ID}/restore")

    assert response.status_code == 200
    assert response.json()["is_active"] is True
