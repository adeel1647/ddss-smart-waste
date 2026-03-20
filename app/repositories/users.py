from __future__ import annotations

from typing import Optional
from sqlalchemy import delete, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import Bin, OrganisationMembership, Site, User, UserBinAssignment, UserSiteAssignment


async def get_user_by_email(db: AsyncSession, email: str) -> Optional[User]:
    res = await db.execute(select(User).where(User.email == email))
    return res.scalar_one_or_none()


async def get_user_by_id(db: AsyncSession, user_id: int) -> Optional[User]:
    res = await db.execute(select(User).where(User.id == user_id))
    return res.scalar_one_or_none()


async def list_users(db: AsyncSession) -> list[User]:
    res = await db.execute(select(User).order_by(User.created_at.desc(), User.id.desc()))
    return list(res.scalars().all())


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
    is_active: bool = True,
) -> User:
    user = User(
        email=email.lower().strip(),
        display_name=display_name,
        password_hash=password_hash,
        is_active=is_active,
        is_admin=is_admin,
    )
    db.add(user)
    await db.flush()
    return user


async def create_membership(
    db: AsyncSession,
    *,
    user_id: int,
    organisation_id: int,
    role: str,
    is_default: bool = False,
) -> OrganisationMembership:
    if is_default:
        await db.execute(update(OrganisationMembership).where(OrganisationMembership.user_id == user_id).values(is_default=False))
    membership = OrganisationMembership(user_id=user_id, organisation_id=organisation_id, role=role, is_default=is_default)
    db.add(membership)
    await db.flush()
    return membership


async def list_user_memberships(db: AsyncSession, user_id: int) -> list[OrganisationMembership]:
    res = await db.execute(select(OrganisationMembership).where(OrganisationMembership.user_id == user_id).order_by(OrganisationMembership.is_default.desc(), OrganisationMembership.created_at.asc()))
    return list(res.scalars().all())


async def replace_user_site_assignments(db: AsyncSession, user_id: int, site_ids: list[int]) -> list[UserSiteAssignment]:
    await db.execute(delete(UserSiteAssignment).where(UserSiteAssignment.user_id == user_id))
    rows=[]
    for site_id in sorted(set(site_ids)):
        row = UserSiteAssignment(user_id=user_id, site_id=site_id)
        db.add(row)
        rows.append(row)
    await db.flush()
    return rows


async def replace_user_bin_assignments(db: AsyncSession, user_id: int, bin_ids: list[str]) -> list[UserBinAssignment]:
    await db.execute(delete(UserBinAssignment).where(UserBinAssignment.user_id == user_id))
    rows=[]
    for bin_id in sorted(set(bin_ids)):
        row = UserBinAssignment(user_id=user_id, bin_id=bin_id)
        db.add(row)
        rows.append(row)
    await db.flush()
    return rows


async def get_user_site_ids(db: AsyncSession, user_id: int) -> list[int]:
    res = await db.execute(select(UserSiteAssignment.site_id).where(UserSiteAssignment.user_id == user_id))
    return list(res.scalars().all())


async def get_user_bin_ids(db: AsyncSession, user_id: int) -> list[str]:
    res = await db.execute(select(UserBinAssignment.bin_id).where(UserBinAssignment.user_id == user_id))
    return list(res.scalars().all())


async def get_accessible_bin_ids(db: AsyncSession, user: User) -> list[str] | None:
    if user.is_admin:
        return None
    memberships = await list_user_memberships(db, user.id)
    role = memberships[0].role if memberships else 'viewer'
    if role in {'manager', 'admin', 'owner'}:
        return None
    direct_bin_ids = set(await get_user_bin_ids(db, user.id))
    site_ids = await get_user_site_ids(db, user.id)
    if site_ids:
        res = await db.execute(select(Bin.bin_id).where(Bin.site_id.in_(site_ids)))
        direct_bin_ids.update(res.scalars().all())
    return sorted(direct_bin_ids)
