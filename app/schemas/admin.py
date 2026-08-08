from pydantic import BaseModel, ConfigDict, EmailStr, Field

from app.schemas.account import AccountRead


class AdminUserCreate(BaseModel):
    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {
                    "email": "new.user@example.com",
                    "full_name": "New User",
                    "password": "strong-password",
                }
            ]
        }
    )

    email: EmailStr = Field(description="Unique email address for the new user.")
    full_name: str = Field(description="User's display name.")
    password: str = Field(description="Plain-text password to hash before storage.")


class AdminUserUpdate(BaseModel):
    model_config = ConfigDict(
        json_schema_extra={"examples": [{"full_name": "Updated User"}]}
    )

    email: EmailStr | None = Field(default=None, description="Replacement unique email address.")
    full_name: str | None = Field(default=None, description="Replacement display name.")
    password: str | None = Field(default=None, description="Replacement plain-text password.")


class AdminUserWithAccountsRead(BaseModel):
    model_config = ConfigDict(
        from_attributes=True,
        json_schema_extra={
            "examples": [
                {
                    "id": 3,
                    "email": "new.user@example.com",
                    "full_name": "New User",
                    "accounts": [{"id": 10, "balance": "150.00"}],
                }
            ]
        },
    )

    id: int = Field(description="User identifier.")
    email: EmailStr = Field(description="User email address.")
    full_name: str = Field(description="User display name.")
    accounts: list[AccountRead] = Field(description="Accounts owned by the user.")
