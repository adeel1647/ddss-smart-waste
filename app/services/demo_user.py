from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import hash_password
from app.db.models import Organisation, OrganisationMembership, User


DEMO_EMAIL = "demo@ddss.com"
DEMO_PASSWORD = "Demo123."
DEMO_NAME = "Demo User"


async def ensure_demo_user(session: AsyncSession) -> None:
    existing = await session.scalar(
        select(User).where(User.email == DEMO_EMAIL)
    )
    if existing:
        return

    first_org = await session.scalar(
        select(Organisation).order_by(Organisation.id.asc()).limit(1)
    )
    if first_org is None:
        return

    user = User(
        email=DEMO_EMAIL,
        password_hash=hash_password(DEMO_PASSWORD),
        display_name=DEMO_NAME,
        is_active=True,
        is_admin=False,
        platform_role=None,
    )
    session.add(user)
    await session.flush()

    membership = OrganisationMembership(
        user_id=user.id,
        organisation_id=first_org.id,
        role="manager",
        is_default=True,
    )
    session.add(membership)
    await session.commit()