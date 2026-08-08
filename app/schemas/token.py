from pydantic import BaseModel, ConfigDict, EmailStr, Field


class LoginRequest(BaseModel):
    model_config = ConfigDict(
        json_schema_extra={"examples": [{"email": "user@example.com", "password": "user-password"}]}
    )

    email: EmailStr = Field(description="Registered email address.")
    password: str = Field(description="Account password.")


class Token(BaseModel):
    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {
                    "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.example.signature",
                    "token_type": "bearer",
                }
            ]
        }
    )

    access_token: str = Field(description="JWT access token for the Authorize dialog.")
    token_type: str = Field(default="bearer", description="Authentication scheme for the token.")
