from typing import cast
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import VoiceRequest


class VoiceRequestRepository:
    async def add(
        self,
        session: AsyncSession,
        *,
        voice_request: VoiceRequest,
    ) -> None:
        session.add(voice_request)
        await session.flush()
        await session.refresh(voice_request)

    async def get_for_household(
        self,
        session: AsyncSession,
        *,
        request_id: UUID,
        household_id: UUID,
        for_update: bool = False,
    ) -> VoiceRequest | None:
        query = select(VoiceRequest).where(
            VoiceRequest.id == request_id,
            VoiceRequest.household_id == household_id,
        )
        if for_update:
            query = query.with_for_update()
        return cast(VoiceRequest | None, await session.scalar(query))

    async def save(
        self,
        session: AsyncSession,
        *,
        voice_request: VoiceRequest,
    ) -> None:
        await session.flush()
        await session.refresh(voice_request)
