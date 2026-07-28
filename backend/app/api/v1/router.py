from fastapi import APIRouter

from app.api.v1.inventory import router as inventory_router
from app.api.v1.inventory_events import router as inventory_events_router
from app.api.v1.inventory_items import router as inventory_items_router
from app.api.v1.voice_requests import router as voice_requests_router

router = APIRouter()
router.include_router(inventory_items_router, prefix="/inventory-items")
router.include_router(inventory_router, prefix="/inventory")
router.include_router(inventory_events_router, prefix="/inventory-events")
router.include_router(voice_requests_router, prefix="/voice-requests")
