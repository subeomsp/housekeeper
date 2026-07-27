from typing import Annotated
from uuid import UUID

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db_session
from app.core.defaults import DEFAULT_HOUSEHOLD_ID, DEFAULT_USER_ID

DatabaseSession = Annotated[AsyncSession, Depends(get_db_session)]


def get_current_household_id() -> UUID:
    return DEFAULT_HOUSEHOLD_ID


def get_current_user_id() -> UUID:
    return DEFAULT_USER_ID


CurrentHouseholdId = Annotated[UUID, Depends(get_current_household_id)]
CurrentUserId = Annotated[UUID, Depends(get_current_user_id)]
