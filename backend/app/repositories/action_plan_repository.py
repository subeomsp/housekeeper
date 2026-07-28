from typing import cast
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import ActionPlan


class ActionPlanRepository:
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
