from pydantic import BaseModel, ConfigDict, EmailStr, Field


class UserRead(BaseModel):
    model_config = ConfigDict(
        from_attributes=True,
        json_schema_extra={
            "examples": [{"id": 1, "email": "user@example.com", "full_name": "Test User"}]
        },
    )

    id: int = Field(description="User identifier.")
    email: EmailStr = Field(description="User email address.")
    full_name: str = Field(description="User display name.")
