from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, get_default_membership, get_user_memberships
from app.core.security import hash_password
from app.db.models import (
    OrganisationMembership,
    PasswordResetCode,
    User,
    UserBinAssignment,
    UserSiteAssignment,
)
from app.db.session import get_session
from app.repositories.users import (
    create_membership,
    create_user,
    get_user_bin_ids,
    get_user_by_email,
    get_user_by_id,
    get_user_site_ids,
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
    return current_user.is_admin or active_role in {'manager', 'admin', 'owner'}


async def _build_user_payload(db: AsyncSession, user: User) -> UserListItemOut:
    memberships = await get_user_memberships(db, user.id)
    default_membership = await get_default_membership(db, user.id)
    active_role = user.platform_role or (default_membership.role if default_membership else 'viewer')
    active_org_id = None if user.platform_role in {'owner', 'admin'} else (default_membership.organisation_id if default_membership else None)
    site_ids = await get_user_site_ids(db, user.id)
    bin_ids = await get_user_bin_ids(db, user.id)
    return UserListItemOut(
        id=user.id,
        email=user.email,
        display_name=user.display_name,
        is_active=user.is_active,
        is_admin=user.is_admin,
        platform_role=user.platform_role,
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


def _is_global_privileged_role(payload: UserListItemOut) -> bool:
    return payload.platform_role in {'owner', 'admin'} or payload.active_role in {'owner', 'admin'}


def _shares_org(payload: UserListItemOut, organisation_id: int | None) -> bool:
    if organisation_id is None:
        return False
    return any(m.organisation_id == organisation_id for m in payload.memberships)


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

        if current_user.platform_role == 'admin':
            if item.platform_role in {'owner', 'admin'} or item.active_role in {'owner', 'admin'}:
                continue

        if me.active_role == 'manager':
            if item.platform_role in {'owner', 'admin'} or item.active_role in {'owner', 'admin'}:
                continue
            if me.active_organisation_id is None:
                continue
            if not _shares_org(item, me.active_organisation_id):
                continue

        if organisation_id is not None:
            if item.platform_role not in {'owner', 'admin'}:
                if not any(m.organisation_id == organisation_id for m in item.memberships):
                    continue

        if role is not None:
            role_matches = item.platform_role == role or item.active_role == role or any(m.role == role for m in item.memberships)
            if not role_matches:
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
        raise HTTPException(status_code=403, detail='Only manager/admin/owner can create users')

    requested_role = (payload.platform_role or payload.role or 'viewer').strip().lower()
    if requested_role not in ALLOWED_ROLES:
        raise HTTPException(status_code=400, detail='Invalid role')

    if me.active_role == 'manager' and requested_role in {'owner', 'admin', 'manager'}:
        raise HTTPException(status_code=403, detail='Manager can only create operator/viewer users')

    if requested_role == 'owner' and current_user.platform_role != 'owner':
        raise HTTPException(status_code=403, detail='Only owner can create another owner')

    existing = await get_user_by_email(db, payload.email.lower().strip())
    if existing:
        raise HTTPException(status_code=409, detail='Email already registered')

    try:
        password_hash = hash_password(payload.password)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    platform_role = requested_role if requested_role in {'owner', 'admin'} else None

    if me.active_role == 'manager':
        if payload.organisation_id is None:
            raise HTTPException(status_code=400, detail='organisation_id is required')
        if payload.organisation_id != me.active_organisation_id:
            raise HTTPException(status_code=403, detail='Manager can only create users in their own organisation')

    user = await create_user(
        db,
        email=payload.email.lower().strip(),
        password_hash=password_hash,
        display_name=payload.display_name,
        is_admin=platform_role in {'owner', 'admin'},
        platform_role=platform_role,
        is_active=payload.is_active,
    )

    if requested_role in {'manager', 'operator', 'viewer'}:
        if payload.organisation_id is None:
            raise HTTPException(status_code=400, detail='organisation_id is required for manager/operator/viewer')
        await create_membership(
            db,
            user_id=user.id,
            organisation_id=payload.organisation_id,
            role=requested_role,
            is_default=payload.is_default_membership,
        )

    if requested_role in {'operator', 'viewer'} and payload.site_ids:
        await replace_user_site_assignments(db, user.id, payload.site_ids)

    await db.commit()
    await db.refresh(user)
    return await _build_user_payload(db, user)


@router.delete('/{user_id}')
async def delete_user(
    user_id: int,
    db: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    me = await _build_user_payload(db, current_user)
    if not _can_manage_users(current_user, me.active_role):
        raise HTTPException(status_code=403, detail='Only manager/admin/owner can delete users')

    target = await get_user_by_id(db, user_id)
    if not target:
        raise HTTPException(status_code=404, detail='User not found')

    if target.id == current_user.id:
        raise HTTPException(status_code=400, detail='You cannot delete your own account')

    target_payload = await _build_user_payload(db, target)
    target_is_global = _is_global_privileged_role(target_payload)

    if current_user.platform_role == 'owner':
        if target.platform_role == 'owner':
            owner_count = await db.scalar(select(func.count(User.id)).where(User.platform_role == 'owner'))
            if (owner_count or 0) <= 1:
                raise HTTPException(status_code=400, detail='Cannot delete the last owner account')
    elif current_user.platform_role == 'admin':
        if target_is_global:
            raise HTTPException(status_code=403, detail='Admin cannot delete owner/admin users')
    elif me.active_role == 'manager':
        if target_is_global or target_payload.active_role == 'manager':
            raise HTTPException(status_code=403, detail='Manager can only delete operator/viewer users')
        if me.active_organisation_id is None:
            raise HTTPException(status_code=403, detail='Manager has no active organisation')
        if not _shares_org(target_payload, me.active_organisation_id):
            raise HTTPException(status_code=403, detail='Manager can only delete users in their own organisation')

    await db.execute(delete(UserSiteAssignment).where(UserSiteAssignment.user_id == user_id))
    await db.execute(delete(UserBinAssignment).where(UserBinAssignment.user_id == user_id))
    await db.execute(delete(OrganisationMembership).where(OrganisationMembership.user_id == user_id))
    await db.execute(delete(PasswordResetCode).where(PasswordResetCode.user_id == user_id))
    await db.delete(target)
    await db.commit()

    return {
        'ok': True,
        'deleted_user_id': user_id,
        'deleted_email': target.email,
        'deleted_role': target_payload.active_role,
    }


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
    if payload.role == 'owner' and current_user.platform_role != 'owner' and me.active_role != 'owner':
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
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail='Only manager/admin/owner can manage assignments')

    target = await get_user_by_id(db, user_id)
    if not target:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail='User not found')

    target_payload = await _build_user_payload(db, target)

    if target_payload.active_role not in {'operator', 'viewer'}:
        raise HTTPException(status_code=400, detail='Assignments are only allowed for operator/viewer')

    if me.active_role == 'manager':
        if me.active_organisation_id is None:
            raise HTTPException(status_code=403, detail='Manager has no active organisation')
        if not any(m.organisation_id == me.active_organisation_id for m in target_payload.memberships):
            raise HTTPException(status_code=403, detail='Manager can only manage users in their own organisation')

    await replace_user_site_assignments(db, user_id, payload.site_ids)
    await replace_user_bin_assignments(db, user_id, [])
    await db.commit()
    return await _build_user_payload(db, target)
