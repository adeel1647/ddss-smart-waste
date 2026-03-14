from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, EmailStr, Field
from sqlalchemy.ext.asyncio import AsyncSession

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
)

router = APIRouter(prefix="/auth", tags=["auth"])


class LoginIn(BaseModel):
    email: EmailStr
    password: str


class TokenOut(BaseModel):
    access_token: str
    token_type: str = "bearer"


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


@router.post("/forgot-password")
async def forgot_password(payload: ForgotIn, db: AsyncSession = Depends(get_session)):
    user = await get_user_by_email(db, payload.email.lower().strip())

    if user:
        reset_token = create_reset_token(subject=str(user.id))
        # TODO: send reset_token by email provider in production
        # For local development only:
        print(f"Password reset token for user {user.email}: {reset_token}")

    return {"message": "If an account with that email exists, a reset link has been sent."}

class ResetIn(BaseModel):
    token: str
    new_password: str = Field(min_length=8, max_length=128)


@router.post("/reset-password")
async def reset_password(payload: ResetIn, db: AsyncSession = Depends(get_session)):
    user_id = decode_reset_token(payload.token)
    if not user_id:
        raise HTTPException(status_code=400, detail="Invalid or expired token")

    user = await get_user_by_id(db, int(user_id))
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    await set_user_password(db, user, hash_password(payload.new_password))
    return {"ok": True}


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


@router.post("/logout")
def logout():
    # Stateless JWT: frontend deletes token
    return {"ok": True}
