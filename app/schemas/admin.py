from pydantic import BaseModel, ConfigDict, EmailStr

from app.schemas.account import AccountRead


class AdminUserCreate(BaseModel):
    email: EmailStr
    full_name: str
    password: str


class AdminUserUpdate(BaseModel):
    email: EmailStr | None = None
    full_name: str | None = None
    password: str | None = None


class AdminUserWithAccountsRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    email: EmailStr
    full_name: str
    accounts: list[AccountRead]
