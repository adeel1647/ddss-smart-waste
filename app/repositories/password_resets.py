from __future__ import annotations

from datetime import datetime, timedelta, timezone

from sqlalchemy import desc, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import PasswordResetCode


async def create_password_reset_code(
    db: AsyncSession,
    *,
    user_id: int,
    code_hash: str,
    expires_in_minutes: int = 10,
) -> PasswordResetCode:
    record = PasswordResetCode(
        user_id=user_id,
        code_hash=code_hash,
        expires_at=datetime.now(timezone.utc) + timedelta(minutes=expires_in_minutes),
        used=False,
        attempts=0,
    )
    db.add(record)
    await db.commit()
    await db.refresh(record)
    return record


async def get_latest_active_reset_code(db: AsyncSession, user_id: int) -> PasswordResetCode | None:
    now = datetime.now(timezone.utc)
    result = await db.execute(
        select(PasswordResetCode)
        .where(
            PasswordResetCode.user_id == user_id,
            PasswordResetCode.used.is_(False),
            PasswordResetCode.expires_at > now,
        )
        .order_by(desc(PasswordResetCode.created_at))
    )
    return result.scalars().first()


async def increment_reset_attempts(db: AsyncSession, record_id: int) -> None:
    await db.execute(
        update(PasswordResetCode)
        .where(PasswordResetCode.id == record_id)
        .values(attempts=PasswordResetCode.attempts + 1)
    )
    await db.commit()


async def mark_reset_code_used(db: AsyncSession, record_id: int) -> None:
    await db.execute(
        update(PasswordResetCode)
        .where(PasswordResetCode.id == record_id)
        .values(used=True)
    )
    await db.commit()
