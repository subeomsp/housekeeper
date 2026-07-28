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
