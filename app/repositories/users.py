from __future__ import annotations

from typing import Optional
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import User


async def get_user_by_email(db: AsyncSession, email: str) -> Optional[User]:
    res = await db.execute(select(User).where(User.email == email))
    return res.scalar_one_or_none()


async def get_user_by_id(db: AsyncSession, user_id: int) -> Optional[User]:
    res = await db.execute(select(User).where(User.id == user_id))
    return res.scalar_one_or_none()


async def update_display_name(db: AsyncSession, user_id: int, display_name: str | None) -> Optional[User]:
    await db.execute(update(User).where(User.id == user_id).values(display_name=display_name))
    await db.commit()
    return await get_user_by_id(db, user_id)


async def set_user_password(db: AsyncSession, user: User, password_hash: str) -> None:
    await db.execute(update(User).where(User.id == user.id).values(password_hash=password_hash))
    await db.commit()


async def create_user(
    db: AsyncSession,
    *,
    email: str,
    password_hash: str,
    display_name: str | None = None,
    is_admin: bool = False,
) -> User:
    user = User(
        email=email.lower().strip(),
        display_name=display_name,
        password_hash=password_hash,
        is_active=True,
        is_admin=is_admin,
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)
    return user