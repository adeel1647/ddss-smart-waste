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


class UserMembershipOut(BaseModel):
    organisation_id: int
    role: str
    is_default: bool
    created_at: str


class UserAssignmentOut(BaseModel):
    site_ids: list[int] = []
    bin_ids: list[str] = []


class UserMeOut(BaseModel):
    id: int
    email: EmailStr
    display_name: str | None = None
    is_active: bool
    is_admin: bool
    active_organisation_id: int | None = None
    active_role: str
    memberships: list[UserMembershipOut]
    assignments: UserAssignmentOut


class UserListItemOut(BaseModel):
    id: int
    email: EmailStr
    display_name: str | None = None
    is_active: bool
    is_admin: bool
    active_role: str
    active_organisation_id: int | None = None
    memberships: list[UserMembershipOut]
    assignments: UserAssignmentOut


class UserCreateWithAccessIn(BaseModel):
    email: EmailStr
    password: str
    display_name: str | None = None
    is_active: bool = True
    is_admin: bool = False
    organisation_id: int | None = None
    role: str = 'viewer'
    is_default_membership: bool = True
    site_ids: list[int] = []
    bin_ids: list[str] = []


class UserMembershipCreateIn(BaseModel):
    organisation_id: int
    role: str = 'viewer'
    is_default: bool = False


class UserAssignmentsUpdateIn(BaseModel):
    site_ids: list[int] = []
    bin_ids: list[str] = []
    replace_existing: bool = True
