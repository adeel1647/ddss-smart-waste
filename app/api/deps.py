from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass

from fastapi import Cookie, Depends, Header, HTTPException, Query, Request, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.db.models import OrganisationMembership, User
from app.db.session import get_session
# from app.models import User, OrganisationMembership

oauth2_scheme = OAuth2PasswordBearer(tokenUrl='/api/v1/auth/login', auto_error=False)

ROLE_ORDER = ['viewer', 'operator', 'manager', 'admin', 'owner']
ROLE_RANK = {role: idx for idx, role in enumerate(ROLE_ORDER, start=1)}

ROLE_PERMISSIONS: dict[str, set[str]] = {
    'viewer': {
        'dashboard:read', 'bin:read', 'alert:read', 'report:read', 'org:read', 'site:read', 'zone:read',
        'analytics:read', 'intelligence:read', 'routing:read', 'ddss:read', 'telemetry:read',
    },
    'operator': {
        'dashboard:read', 'bin:read', 'alert:read', 'report:read', 'org:read', 'site:read', 'zone:read',
        'analytics:read', 'intelligence:read', 'routing:read', 'ddss:read', 'telemetry:read',
        'device:read', 'device:heartbeat', 'work_order:read', 'work_order:update_assigned',
        'contamination:read', 'contamination:write',
    },
    'manager': {
        'dashboard:read', 'bin:read', 'bin:write', 'alert:read', 'alert:write', 'report:read', 'report:write',
        'org:read', 'site:read', 'site:write', 'zone:read', 'zone:write',
        'device:read', 'device:write', 'audit:read', 'work_order:read', 'work_order:write',
        'intelligence:read', 'analytics:read', 'contamination:read', 'contamination:write',
        'membership:read', 'membership:write_limited',
        'routing:read', 'routing:write', 'ddss:read', 'ddss:write', 'telemetry:read', 'telemetry:write',
        'classify:read', 'classify:write',
    },
    'admin': {
        'dashboard:read', 'bin:read', 'bin:write', 'alert:read', 'alert:write', 'report:read', 'report:write',
        'org:read', 'org:write', 'site:read', 'site:write', 'zone:read', 'zone:write',
        'device:read', 'device:write', 'device:heartbeat', 'notification:read', 'notification:write',
        'audit:read', 'work_order:read', 'work_order:write', 'intelligence:read', 'analytics:read',
        'membership:read', 'membership:write', 'contamination:read', 'contamination:write',
        'model_monitoring:read', 'routing:read', 'routing:write', 'ddss:read', 'ddss:write',
        'telemetry:read', 'telemetry:write', 'classify:read', 'classify:write',
    },
    'owner': {
        'dashboard:read', 'bin:read', 'bin:write', 'alert:read', 'alert:write', 'report:read', 'report:write',
        'org:read', 'org:write', 'org:delete', 'site:read', 'site:write', 'zone:read', 'zone:write',
        'device:read', 'device:write', 'device:heartbeat', 'notification:read', 'notification:write',
        'audit:read', 'work_order:read', 'work_order:write', 'intelligence:read', 'analytics:read',
        'membership:read', 'membership:write', 'membership:assign_owner',
        'contamination:read', 'contamination:write', 'model_monitoring:read', 'model_monitoring:write',
        'routing:read', 'routing:write', 'ddss:read', 'ddss:write', 'telemetry:read', 'telemetry:write',
        'classify:read', 'classify:write',
    },
}

@dataclass(slots=True)
class RequestOrgContext:
    organisation_id: int | None
    role: str
    membership: OrganisationMembership | None


def _unauthorized(detail: str = 'Could not validate credentials') -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail=detail,
        headers={'WWW-Authenticate': 'Bearer'},
    )


def _forbidden(detail: str) -> HTTPException:
    return HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=detail)


def get_client_ip(request: Request) -> str:
    forwarded_for = request.headers.get('x-forwarded-for')
    if forwarded_for:
        return forwarded_for.split(',')[0].strip()
    if request.client and request.client.host:
        return request.client.host
    return 'unknown'


async def get_bearer_token(
    authorization: str | None = Header(default=None),
    oauth_token: str | None = Depends(oauth2_scheme),
    access_cookie: str | None = Cookie(default=None, alias=settings.token_cookie_name),
) -> str | None:
    if authorization and authorization.lower().startswith('bearer '):
        return authorization.split(' ', 1)[1].strip()
    if oauth_token:
        return oauth_token
    if access_cookie:
        return access_cookie
    return None


async def get_current_user(
    token: str | None = Depends(get_bearer_token),
    session: AsyncSession = Depends(get_session),
) -> User:
    if not token:
        raise _unauthorized('Authentication required')

    try:
        payload = jwt.decode(token, settings.jwt_secret, algorithms=[settings.jwt_algorithm])
        user_id = payload.get('sub')
        if user_id is None:
            raise _unauthorized()
    except JWTError as exc:
        raise _unauthorized() from exc

    result = await session.execute(select(User).where(User.id == int(user_id)))
    user = result.scalar_one_or_none()
    if user is None or not user.is_active:
        raise _unauthorized()
    return user




async def get_current_user_optional(
    token: str | None = Depends(get_bearer_token),
    session: AsyncSession = Depends(get_session),
) -> User | None:
    if not token:
        return None
    try:
        payload = jwt.decode(token, settings.jwt_secret, algorithms=[settings.jwt_algorithm])
        user_id = payload.get('sub')
        if user_id is None:
            return None
    except JWTError:
        return None
    result = await session.execute(select(User).where(User.id == int(user_id)))
    user = result.scalar_one_or_none()
    if user is None or not user.is_active:
        return None
    return user

async def require_admin(current_user: User = Depends(get_current_user)) -> User:
    if not current_user.is_admin:
        raise _forbidden('Admin access required')
    return current_user


async def require_internal_api_key(x_api_key: str | None = Header(default=None, alias='X-API-Key')) -> None:
    if not settings.internal_api_key:
        return
    if x_api_key != settings.internal_api_key:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail='Invalid API key')


async def get_user_memberships(session: AsyncSession, user_id: int) -> list[OrganisationMembership]:
    result = await session.execute(
        select(OrganisationMembership)
        .where(OrganisationMembership.user_id == user_id)
        .order_by(OrganisationMembership.is_default.desc(), OrganisationMembership.created_at.asc())
    )
    return list(result.scalars().all())


async def get_user_membership(
    session: AsyncSession,
    user_id: int,
    organisation_id: int,
) -> OrganisationMembership | None:
    result = await session.execute(
        select(OrganisationMembership).where(
            OrganisationMembership.user_id == user_id,
            OrganisationMembership.organisation_id == organisation_id,
        )
    )
    return result.scalar_one_or_none()


async def get_default_membership(session: AsyncSession, user_id: int) -> OrganisationMembership | None:
    result = await session.execute(
        select(OrganisationMembership)
        .where(OrganisationMembership.user_id == user_id)
        .order_by(OrganisationMembership.is_default.desc(), OrganisationMembership.created_at.asc())
        .limit(1)
    )
    return result.scalar_one_or_none()


async def get_active_org_context(
    db: AsyncSession,
    user: User,
    organisation_id: int | None = None,
):
    if user.platform_role in {'owner', 'admin'}:
        return RequestOrgContext(
            organisation_id=organisation_id,
            role=user.platform_role,
            membership=None,
        )

    query = select(OrganisationMembership).where(OrganisationMembership.user_id == user.id)
    if organisation_id is not None:
        query = query.where(OrganisationMembership.organisation_id == organisation_id)
    else:
        query = query.where(OrganisationMembership.is_default == True)

    result = await db.execute(query)
    membership = result.scalars().first()
    if not membership:
        raise HTTPException(status_code=403, detail='No organisation access')

    return RequestOrgContext(
        organisation_id=membership.organisation_id,
        role=membership.role,
        membership=membership,
    )


async def get_active_role(  
    session: AsyncSession,
    user: User,
    organisation_id: int | None = None,
) -> str:
    ctx = await get_active_org_context(session, user, organisation_id)
    return ctx.role


def role_has_permission(role: str, permission: str) -> bool:
    if role in {'owner', 'admin'}:
        return True
    return permission in ROLE_PERMISSIONS.get(role, set())


def role_in(role: str, allowed_roles: Iterable[str]) -> bool:
    if role in {'owner', 'admin'}:
        return True
    return role in set(allowed_roles)


async def require_org_permission(
    session: AsyncSession,
    user: User,
    organisation_id: int,
    permission: str,
) -> OrganisationMembership | None:
    ctx = await get_active_org_context(session, user, organisation_id)
    if not role_has_permission(ctx.role, permission):
        raise _forbidden(f'Missing permission: {permission}')
    return ctx


async def require_org_role(
    session: AsyncSession,
    user: User,
    organisation_id: int,
    minimum_role: str,
) -> OrganisationMembership | None:
    ctx = await get_active_org_context(session, user, organisation_id)
    if user.platform_role in {'owner', 'admin'}:
        return None
    if ROLE_RANK.get(ctx.role, 0) < ROLE_RANK.get(minimum_role, 0):
        raise _forbidden(f'Requires role {minimum_role} or higher')
    return ctx.membership


async def require_org_any_role(
    session: AsyncSession,
    user: User,
    organisation_id: int,
    allowed_roles: Iterable[str],
) -> OrganisationMembership | None:
    ctx = await get_active_org_context(session, user, organisation_id)
    if not role_in(ctx.role, allowed_roles):
        raise _forbidden('You do not have access to perform this action')
    return ctx.membership


async def assert_any_org_permission(
    session: AsyncSession,
    user: User,
    organisation_ids: Iterable[int],
    permission: str,
) -> int | None:
    ids = [int(org_id) for org_id in organisation_ids]
    if user.platform_role in {'owner', 'admin'}:
        return ids[0] if ids else None
    memberships = await get_user_memberships(session, user.id)
    for membership in memberships:
        if membership.organisation_id in ids and role_has_permission(membership.role, permission):
            return membership.organisation_id
    raise _forbidden(f'No organisation access with permission {permission}')


async def get_requested_org_id(
    session: AsyncSession,
    user: User,
    organisation_id: int | None = Query(default=None),
) -> int | None:
    ctx = await get_active_org_context(session, user, organisation_id)
    return ctx.organisation_id

def require_roles(*roles: str):
    async def checker(
        db: AsyncSession = Depends(get_session),
        user: User = Depends(get_current_user),
    ):
        if user.platform_role in {'owner', 'admin'}:
            if user.platform_role in roles or 'owner' in roles or 'admin' in roles:
                return user
        ctx = await get_active_org_context(db, user)
        if ctx.role not in roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f'Requires role {roles}',
            )
        return user
    return checker