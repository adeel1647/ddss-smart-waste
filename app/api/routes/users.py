from fastapi import APIRouter, Depends
from pydantic import BaseModel, EmailStr
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.db.session import get_session
from app.repositories.users import update_display_name

router = APIRouter(prefix="/users", tags=["users"])


class UserMeOut(BaseModel):
    email: EmailStr
    display_name: str | None = None


class UserMeUpdate(BaseModel):
    display_name: str | None = None


@router.get("/me", response_model=UserMeOut)
async def me(user=Depends(get_current_user)):
    return {"email": user.email, "display_name": user.display_name}


@router.patch("/me", response_model=UserMeOut)
async def update_me(
    payload: UserMeUpdate,
    user=Depends(get_current_user),
    db: AsyncSession = Depends(get_session),
):
    updated = await update_display_name(db, user.id, payload.display_name)
    return {"email": updated.email, "display_name": updated.display_name}