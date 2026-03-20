from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, get_default_membership, get_user_memberships
from app.core.security import hash_password
from app.db.models import User
from app.db.session import get_session
from app.repositories.users import (
    create_membership,
    create_user,
    get_user_bin_ids,
    get_user_by_email,
    get_user_by_id,
    get_user_site_ids,
    list_user_memberships,
    list_users as repo_list_users,
    replace_user_bin_assignments,
    replace_user_site_assignments,
    update_display_name,
)
from app.schemas.users import (
    UserAssignmentOut,
    UserAssignmentsUpdateIn,
    UserCreateWithAccessIn,
    UserListItemOut,
    UserMeOut,
    UserMembershipCreateIn,
    UserMembershipOut,
)

router = APIRouter(prefix='/users', tags=['users'])

ALLOWED_ROLES = {'viewer', 'operator', 'manager', 'admin', 'owner'}


def _can_manage_users(current_user: User, active_role: str | None) -> bool:
    return current_user.is_admin or active_role in {'admin', 'owner'}


async def _build_user_payload(db: AsyncSession, user: User) -> UserListItemOut:
    memberships = await get_user_memberships(db, user.id)
    default_membership = await get_default_membership(db, user.id)
    active_role = 'owner' if user.is_admin else (default_membership.role if default_membership else 'viewer')
    active_org_id = None if user.is_admin else (default_membership.organisation_id if default_membership else None)
    site_ids = await get_user_site_ids(db, user.id)
    bin_ids = await get_user_bin_ids(db, user.id)
    return UserListItemOut(
        id=user.id,
        email=user.email,
        display_name=user.display_name,
        is_active=user.is_active,
        is_admin=user.is_admin,
        active_organisation_id=active_org_id,
        active_role=active_role,
        memberships=[
            UserMembershipOut(
                organisation_id=m.organisation_id,
                role=m.role,
                is_default=m.is_default,
                created_at=m.created_at.isoformat(),
            )
            for m in memberships
        ],
        assignments=UserAssignmentOut(site_ids=site_ids, bin_ids=bin_ids),
    )


@router.get('/me', response_model=UserMeOut)
async def me(user: User = Depends(get_current_user), db: AsyncSession = Depends(get_session)):
    return await _build_user_payload(db, user)


@router.patch('/me', response_model=UserMeOut)
async def update_me(
    payload: dict,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_session),
):
    updated = await update_display_name(db, user.id, payload.get('display_name'))
    return await _build_user_payload(db, updated)


@router.get('', response_model=list[UserListItemOut])
async def list_users(
    organisation_id: int | None = Query(default=None),
    role: str | None = Query(default=None),
    db: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    me = await _build_user_payload(db, current_user)
    if not _can_manage_users(current_user, me.active_role):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail='Only admin/owner can list all users')

    rows = await repo_list_users(db)
    items: list[UserListItemOut] = []
    for row in rows:
        item = await _build_user_payload(db, row)
        if organisation_id is not None and not any(m.organisation_id == organisation_id for m in item.memberships):
            continue
        if role is not None and not any(m.role == role for m in item.memberships):
            continue
        items.append(item)
    return items


@router.post('', response_model=UserListItemOut, status_code=status.HTTP_201_CREATED)
async def create_user_with_access(
    payload: UserCreateWithAccessIn,
    db: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    me = await _build_user_payload(db, current_user)
    if not _can_manage_users(current_user, me.active_role):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail='Only admin/owner can create users')
    if payload.role not in ALLOWED_ROLES:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail='Invalid role')
    if payload.role == 'owner' and not (current_user.is_admin or me.active_role == 'owner'):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail='Only owner/platform admin can assign owner role')
    existing = await get_user_by_email(db, payload.email.lower().strip())
    if existing:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail='Email already registered')
    password_hash = hash_password(payload.password)
    user = await create_user(db, email=payload.email, password_hash=password_hash, display_name=payload.display_name, is_admin=payload.is_admin, is_active=payload.is_active)
    if payload.organisation_id is not None:
        await create_membership(db, user_id=user.id, organisation_id=payload.organisation_id, role=payload.role, is_default=payload.is_default_membership)
    if payload.site_ids:
        await replace_user_site_assignments(db, user.id, payload.site_ids)
    if payload.bin_ids:
        await replace_user_bin_assignments(db, user.id, payload.bin_ids)
    await db.commit()
    await db.refresh(user)
    return await _build_user_payload(db, user)


@router.post('/{user_id}/memberships', response_model=UserListItemOut)
async def add_membership(
    user_id: int,
    payload: UserMembershipCreateIn,
    db: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    me = await _build_user_payload(db, current_user)
    if not _can_manage_users(current_user, me.active_role):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail='Only admin/owner can assign memberships')
    if payload.role not in ALLOWED_ROLES:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail='Invalid role')
    if payload.role == 'owner' and not (current_user.is_admin or me.active_role == 'owner'):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail='Only owner/platform admin can assign owner role')
    target = await get_user_by_id(db, user_id)
    if not target:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail='User not found')
    await create_membership(db, user_id=user_id, organisation_id=payload.organisation_id, role=payload.role, is_default=payload.is_default)
    await db.commit()
    return await _build_user_payload(db, target)


@router.post('/{user_id}/assignments', response_model=UserListItemOut)
async def update_assignments(
    user_id: int,
    payload: UserAssignmentsUpdateIn,
    db: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    me = await _build_user_payload(db, current_user)
    if not _can_manage_users(current_user, me.active_role):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail='Only admin/owner can manage assignments')
    target = await get_user_by_id(db, user_id)
    if not target:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail='User not found')
    await replace_user_site_assignments(db, user_id, payload.site_ids)
    await replace_user_bin_assignments(db, user_id, payload.bin_ids)
    await db.commit()
    return await _build_user_payload(db, target)
