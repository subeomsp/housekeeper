from typing import Any
from uuid import UUID, uuid4

from sqlalchemy.ext.asyncio import AsyncSession

from app.models import AuditLog


class AuditLogRepository:
    async def add(
        self,
        session: AsyncSession,
        *,
        household_id: UUID,
        user_id: UUID | None,
        action: str,
        target_type: str,
        target_id: UUID,
        before_json: dict[str, Any] | None,
        after_json: dict[str, Any] | None,
    ) -> AuditLog:
        audit_log = AuditLog(
            id=uuid4(),
            household_id=household_id,
            user_id=user_id,
            action=action,
            target_type=target_type,
            target_id=target_id,
            before_json=before_json,
            after_json=after_json,
        )
        session.add(audit_log)
        await session.flush()
        return audit_log

