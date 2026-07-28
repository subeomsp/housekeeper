from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock
from uuid import UUID

from fastapi import FastAPI
from httpx import AsyncClient

from app.services.voice_request_service import (
    TextVoiceRequestView,
    VoiceRequestService,
    get_voice_request_service,
)

REQUEST_ID = UUID("00000000-0000-4000-8000-000000000501")
CREATED_AT = datetime(2026, 7, 28, 12, 0, tzinfo=UTC)


async def test_create_text_voice_request_returns_planning_request(
    app: FastAPI,
    client: AsyncClient,
) -> None:
    service = MagicMock(spec=VoiceRequestService)
    service.create_text_request = AsyncMock(
        return_value=TextVoiceRequestView(
            request_id=REQUEST_ID,
            transcript="우유 두 개 사왔어.",
            status="planning",
            created_at=CREATED_AT,
        )
    )
    app.dependency_overrides[get_voice_request_service] = lambda: service

    response = await client.post(
        "/api/v1/voice-requests/text",
        json={"transcript": " 우유 두 개 사왔어. "},
    )

    assert response.status_code == 201
    assert response.json() == {
        "request_id": str(REQUEST_ID),
        "transcript": "우유 두 개 사왔어.",
        "status": "planning",
        "created_at": "2026-07-28T12:00:00Z",
    }
    service.create_text_request.assert_awaited_once()


async def test_create_text_voice_request_rejects_blank_transcript(
    client: AsyncClient,
) -> None:
    response = await client.post(
        "/api/v1/voice-requests/text",
        json={"transcript": "   "},
    )

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "VALIDATION_ERROR"
