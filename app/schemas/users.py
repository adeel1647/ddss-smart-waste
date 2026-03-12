from pydantic import BaseModel, EmailStr


class UserCreate(BaseModel):
    email: EmailStr
    password: str
    display_name: str | None = None


class UserOut(BaseModel):
    id: int
    email: EmailStr
    display_name: str | None = None
    is_active: bool
    is_admin: bool

    class Config:
        from_attributes = True