from __future__ import annotations

import logging
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from pydantic import BaseModel, EmailStr, Field
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_bearer_token, get_client_ip, get_current_user, get_current_user_optional
from app.core.config import settings
from app.core.rate_limit import enforce_rate_limit
from app.core.security import (
    create_access_token,
    create_reset_token,
    generate_verification_code,
    hash_password,
    hash_verification_code,
    verify_password,
    verify_verification_code,
    decode_reset_token,
)
from app.db.models import Organisation, OrganisationMembership, User
from app.db.session import get_session
from app.repositories.password_resets import (
    create_password_reset_code,
    get_latest_active_reset_code,
    increment_reset_attempts,
    mark_reset_code_used,
)
from app.repositories.users import create_membership, create_user, get_user_by_email, get_user_by_id, set_user_password
from app.schemas.users import UserOut
from app.services.email_service import send_reset_code_email

router = APIRouter(prefix='/auth', tags=['auth'])
log = logging.getLogger('app.auth')

GENERIC_RESET_MESSAGE = 'If an account exists for that email, a verification code has been sent.'


def _slugify_org_name(value: str) -> str:
    import re

    value = (value or '').strip().lower()
    value = re.sub(r'[^a-z0-9]+', '-', value)
    value = re.sub(r'-{2,}', '-', value).strip('-')
    return value or 'default-organisation'


async def _make_unique_org_slug(db: AsyncSession, base_name: str) -> str:
    base = _slugify_org_name(base_name)
    slug = base
    suffix = 2
    while True:
        res = await db.execute(select(Organisation.id).where(Organisation.slug == slug))
        if res.scalar_one_or_none() is None:
            return slug
        slug = f'{base}-{suffix}'
        suffix += 1


async def _is_admin_or_owner(db: AsyncSession, user_id: int) -> bool:
    user = await db.get(User, user_id)
    if user and user.platform_role in {'owner', 'admin'}:
        return True

    res = await db.execute(
        select(OrganisationMembership.role).where(OrganisationMembership.user_id == user_id)
    )
    roles = {role for (role,) in res.all()}
    return bool(roles.intersection({'owner', 'admin'}))

    
class LoginIn(BaseModel):
    email: EmailStr
    password: str


class TokenOut(BaseModel):
    access_token: str
    token_type: str = 'bearer'


class ForgotPasswordRequestIn(BaseModel):
    email: EmailStr


class VerifyResetCodeIn(BaseModel):
    email: EmailStr
    code: str = Field(min_length=6, max_length=6)


class ResetPasswordWithCodeIn(BaseModel):
    reset_token: str
    new_password: str = Field(min_length=8, max_length=128)
    confirm_password: str = Field(min_length=8, max_length=128)


class RegisterIn(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)
    display_name: str | None = None
    role: str = 'viewer'
    organisation_id: int | None = None


class SessionOut(BaseModel):
    authenticated: bool
    user: UserOut | None = None


def _auth_limit_key(kind: str, ip: str, email: str | None = None) -> str:
    suffix = f':{email.lower().strip()}' if email else ''
    return f'auth:{kind}:{ip}{suffix}'


def _set_auth_cookie(response: Response, token: str) -> None:
    response.set_cookie(
        key=settings.token_cookie_name,
        value=token,
        httponly=True,
        secure=settings.cookie_secure,
        samesite=settings.cookie_samesite,
        max_age=settings.access_token_expire_minutes * 60,
    )


@router.get('/session', response_model=SessionOut)
async def session_status(current_user: User = Depends(get_current_user)):
    return SessionOut(authenticated=True, user=current_user)


@router.post('/login', response_model=TokenOut)
async def login(payload: LoginIn, response: Response, request: Request, db: AsyncSession = Depends(get_session)):
    client_ip = get_client_ip(request)
    normalized_email = payload.email.lower().strip()
    enforce_rate_limit(
        _auth_limit_key('login', client_ip, normalized_email),
        limit=settings.auth_login_max_attempts,
        window_seconds=settings.auth_rate_limit_window_seconds,
        detail='Too many login attempts. Please try again later.',
    )

    user = await get_user_by_email(db, normalized_email)
    if not user or not verify_password(payload.password, user.password_hash):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail='Invalid credentials')
    if not user.is_active:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail='User inactive')

    token = create_access_token(
        subject=str(user.id),
        email=user.email,
        role=user.platform_role or 'user',
    )
    _set_auth_cookie(response, token)
    return TokenOut(access_token=token)


@router.post('/register', response_model=UserOut, status_code=status.HTTP_201_CREATED)
async def register_user(
    payload: RegisterIn,
    db: AsyncSession = Depends(get_session),
    current_user: User | None = Depends(get_current_user_optional),
):
    normalized_email = payload.email.lower().strip()
    display_name = payload.display_name.strip() if payload.display_name else None

    existing = await get_user_by_email(db, normalized_email)
    if existing:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail='Email already registered')

    password_hash = hash_password(payload.password)

    requested_role = (payload.role or 'viewer').strip().lower()
    if requested_role not in {'viewer', 'operator', 'manager', 'admin', 'owner'}:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail='Invalid role')

    user_count_res = await db.execute(select(func.count()).select_from(User))
    is_bootstrap = user_count_res.scalar_one() == 0

    if is_bootstrap:
        user = await create_user(
            db,
            email=normalized_email,
            password_hash=password_hash,
            display_name=display_name,
            is_admin=True,
            platform_role='owner',
        )
        await db.commit()
        await db.refresh(user)
        return user

    wants_managed_creation = requested_role != 'viewer' or payload.organisation_id is not None
    if wants_managed_creation:
        if current_user is None or not await _is_admin_or_owner(db, current_user.id):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail='Only authenticated admins/owners can register users with roles',
            )

    platform_role = requested_role if requested_role in {'owner', 'admin'} else None
    user = await create_user(
        db,
        email=normalized_email,
        password_hash=password_hash,
        display_name=display_name,
        is_admin=platform_role in {'owner', 'admin'},
        platform_role=platform_role,
    )

    if requested_role in {'manager', 'operator', 'viewer'}:
        if payload.organisation_id is None:
            raise HTTPException(status_code=400, detail='organisation_id is required for manager/operator/viewer')
        await create_membership(
            db,
            user_id=user.id,
            organisation_id=payload.organisation_id,
            role=requested_role,
            is_default=True,
        )

    await db.commit()
    await db.refresh(user)
    return user


@router.post('/forgot-password/request-code')
async def request_password_reset_code(payload: ForgotPasswordRequestIn, request: Request, db: AsyncSession = Depends(get_session)):
    client_ip = get_client_ip(request)
    email = payload.email.lower().strip()
    enforce_rate_limit(
        _auth_limit_key('reset-request', client_ip, email),
        limit=settings.reset_request_max_attempts,
        window_seconds=settings.auth_rate_limit_window_seconds,
        detail='Too many reset requests. Please try again later.',
    )

    user = await get_user_by_email(db, email)

    if user:
        code = generate_verification_code()
        code_hash = hash_verification_code(code)
        await create_password_reset_code(db, user_id=user.id, code_hash=code_hash, expires_in_minutes=10)
        send_reset_code_email(user.email, code)

    return {'message': GENERIC_RESET_MESSAGE}


@router.post('/forgot-password/verify-code')
async def verify_password_reset_code(payload: VerifyResetCodeIn, request: Request, db: AsyncSession = Depends(get_session)):
    client_ip = get_client_ip(request)
    email = payload.email.lower().strip()
    enforce_rate_limit(
        _auth_limit_key('reset-verify', client_ip, email),
        limit=settings.reset_verify_max_attempts,
        window_seconds=settings.auth_rate_limit_window_seconds,
        detail='Too many verification attempts. Please try again later.',
    )

    user = await get_user_by_email(db, email)
    if not user:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail='Invalid email or verification code')

    record = await get_latest_active_reset_code(db, user.id)
    if not record:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail='Invalid email or verification code')

    if record.attempts >= 5:
        raise HTTPException(status_code=status.HTTP_429_TOO_MANY_REQUESTS, detail='Too many attempts')

    if record.expires_at < datetime.now(timezone.utc):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail='Invalid email or verification code')

    if not verify_verification_code(payload.code, record.code_hash):
        await increment_reset_attempts(db, record.id)
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail='Invalid email or verification code')

    reset_token = create_reset_token(subject=str(user.id))
    return {'message': 'Code verified successfully', 'reset_token': reset_token}


@router.post('/forgot-password/reset')
async def reset_password_with_verified_code(payload: ResetPasswordWithCodeIn, db: AsyncSession = Depends(get_session)):
    if payload.new_password != payload.confirm_password:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail='Passwords do not match')

    user_id = decode_reset_token(payload.reset_token)
    if not user_id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail='Invalid or expired reset token')

    user = await get_user_by_id(db, int(user_id))
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail='User not found')

    try:
        new_hash = hash_password(payload.new_password)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc

    await set_user_password(db, user, new_hash)

    record = await get_latest_active_reset_code(db, user.id)
    if record:
        await mark_reset_code_used(db, record.id)

    return {'message': 'Password reset successful'}


@router.post('/logout')
async def logout(response: Response):
    response.delete_cookie(settings.token_cookie_name)
    return {'ok': True}
