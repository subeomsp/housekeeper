from typing import cast
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import ActionPlan, VoiceRequest


class ActionPlanRepository:
    async def get_for_household(
        self,
        session: AsyncSession,
        *,
        request_id: UUID,
        household_id: UUID,
        for_update: bool = False,
    ) -> ActionPlan | None:
        query = (
            select(ActionPlan)
            .join(VoiceRequest, VoiceRequest.id == ActionPlan.voice_request_id)
            .where(
                ActionPlan.voice_request_id == request_id,
                VoiceRequest.household_id == household_id,
            )
        )
        if for_update:
            query = query.with_for_update(of=ActionPlan)
        return cast(ActionPlan | None, await session.scalar(query))

    async def get_by_voice_request(
        self,
        session: AsyncSession,
        *,
        voice_request_id: UUID,
    ) -> ActionPlan | None:
        return cast(
            ActionPlan | None,
            await session.scalar(
                select(ActionPlan).where(ActionPlan.voice_request_id == voice_request_id)
            ),
        )

    async def add(
        self,
        session: AsyncSession,
        *,
        action_plan: ActionPlan,
    ) -> None:
        session.add(action_plan)
        await session.flush()
        await session.refresh(action_plan)

    async def save(
        self,
        session: AsyncSession,
        *,
        action_plan: ActionPlan,
    ) -> None:
        await session.flush()
        await session.refresh(action_plan)
