from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from app.repositories.enterprise import create_audit_log


async def log_audit(
    session: AsyncSession,
    *,
    organisation_id: int | None,
    actor_user_id: int | None,
    action: str,
    entity_type: str,
    entity_id: str | None,
    status: str = 'success',
    details: dict | None = None,
):
    await create_audit_log(
        session,
        organisation_id=organisation_id,
        actor_user_id=actor_user_id,
        action=action,
        entity_type=entity_type,
        entity_id=entity_id,
        status=status,
        details=details or {},
    )
