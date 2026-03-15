from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, EmailStr, Field
from sqlalchemy.ext.asyncio import AsyncSession
from jose import jwt
from datetime import datetime 
from app.core.config import settings
from app.db.session import get_session
from app.repositories.users import (
    get_user_by_email,
    get_user_by_id,
    set_user_password,
    create_user,
)
from app.schemas.users import UserOut
from app.core.security import (
    hash_password,
    verify_password,
    create_access_token,
    create_reset_token,
    decode_reset_token,
    generate_verification_code,
    hash_verification_code,
    verify_verification_code,
)
from app.repositories.password_resets import (
    create_password_reset_code,
    get_latest_active_reset_code,
    increment_reset_attempts,
    mark_reset_code_used,
)
from app.services.email_service import send_reset_code_email

router = APIRouter(prefix="/auth", tags=["auth"])


class LoginIn(BaseModel):
    email: EmailStr
    password: str


class TokenOut(BaseModel):
    access_token: str
    token_type: str = "bearer"

class ForgotPasswordRequestIn(BaseModel):
    email: EmailStr


class VerifyResetCodeIn(BaseModel):
    email: EmailStr
    code: str = Field(min_length=6, max_length=6)


class ResetPasswordWithCodeIn(BaseModel):
    reset_token: str
    new_password: str = Field(min_length=8, max_length=128)
    confirm_password: str = Field(min_length=8, max_length=128)


@router.post("/login", response_model=TokenOut)
async def login(payload: LoginIn, db: AsyncSession = Depends(get_session)):
    user = await get_user_by_email(db, payload.email.lower().strip())
    if not user or not verify_password(payload.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Invalid credentials")
    if not user.is_active:
        raise HTTPException(status_code=403, detail="User inactive")

    token = create_access_token(subject=str(user.id), email=user.email)
    return TokenOut(access_token=token)


class ForgotIn(BaseModel):
    email: EmailStr

class RegisterIn(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)
    display_name: str | None = None

@router.post("/register", response_model=UserOut, status_code=status.HTTP_201_CREATED)
async def register_user(payload: RegisterIn, db: AsyncSession = Depends(get_session)):

    existing = await get_user_by_email(db, payload.email.lower())
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Email already registered",
        )
    try:
        pw_hash = hash_password(payload.password)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    # create user
    user = await create_user(
        db,
        email=payload.email,
        password_hash=pw_hash,
        display_name=payload.display_name,
    )

    return user


@router.post("/forgot-password/request-code")
async def request_password_reset_code(
    payload: ForgotPasswordRequestIn,
    db: AsyncSession = Depends(get_session),
):
    email = payload.email.lower().strip()
    user = await get_user_by_email(db, email)

    if not user:
        raise HTTPException(
            status_code=404,
            detail="Account with this email does not exist",
        )

    code = generate_verification_code()
    code_hash = hash_verification_code(code)

    await create_password_reset_code(
        db,
        user_id=user.id,
        code_hash=code_hash,
        expires_in_minutes=10,
    )

    send_reset_code_email(user.email, code)

    return {
        "message": "Verification code sent to your email"
    }

@router.post("/forgot-password/verify-code")
async def verify_password_reset_code(
    payload: VerifyResetCodeIn,
    db: AsyncSession = Depends(get_session),
):
    user = await get_user_by_email(db, payload.email.lower().strip())
    if not user:
        raise HTTPException(status_code=404, detail="Account with this email does not exist")

    record = await get_latest_active_reset_code(db, user.id)
    if not record:
        raise HTTPException(status_code=400, detail="No reset code found")

    if record.used:
        raise HTTPException(status_code=400, detail="Code already used")

    from datetime import datetime, timezone
    if record.expires_at < datetime.now(timezone.utc):
        raise HTTPException(status_code=400, detail="Code expired")

    if record.attempts >= 5:
        raise HTTPException(status_code=429, detail="Too many attempts")

    if not verify_verification_code(payload.code, record.code_hash):
        await increment_reset_attempts(db, record.id)
        raise HTTPException(status_code=400, detail="Invalid code")

    reset_token = create_reset_token(subject=str(user.id))

    return {
        "message": "Code verified successfully",
        "reset_token": reset_token,
    }

@router.post("/forgot-password/reset")
async def reset_password_with_verified_code(
    payload: ResetPasswordWithCodeIn,
    db: AsyncSession = Depends(get_session),
):
    if payload.new_password != payload.confirm_password:
        raise HTTPException(status_code=400, detail="Passwords do not match")

    user_id = decode_reset_token(payload.reset_token)
    if not user_id:
        raise HTTPException(status_code=400, detail="Invalid or expired reset token")

    user = await get_user_by_id(db, int(user_id))
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    new_hash = hash_password(payload.new_password)
    await set_user_password(db, user, new_hash)

    record = await get_latest_active_reset_code(db, user.id)
    if record and not record.used:
        await mark_reset_code_used(db, record.id)

    return {"message": "Password reset successful"}



@router.post("/logout")
def logout():
    # Stateless JWT: frontend deletes token
    return {"ok": True}
