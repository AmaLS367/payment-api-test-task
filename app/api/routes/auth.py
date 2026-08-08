from fastapi import APIRouter, HTTPException, status

from app.api.deps import DbSession
from app.core.security import create_access_token, verify_password
from app.schemas.token import LoginRequest, Token
from app.services.user import get_user_by_email

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/login", response_model=Token)
async def login(payload: LoginRequest, db: DbSession) -> Token:
    user = await get_user_by_email(db, payload.email)
    if user is None or not verify_password(payload.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return Token(access_token=create_access_token(subject=str(user.id)))
