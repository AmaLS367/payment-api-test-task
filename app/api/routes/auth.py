from fastapi import APIRouter, HTTPException, status

from app.api.deps import DbSession
from app.api.openapi import UNAUTHORIZED_RESPONSE, VALIDATION_ERROR_RESPONSE
from app.core.security import create_access_token, verify_password
from app.schemas.token import LoginRequest, Token
from app.services.user import get_user_by_email

router = APIRouter(prefix="/auth", tags=["Auth"])


@router.post(
    "/login",
    response_model=Token,
    summary="Sign in and obtain a Bearer token",
    description="Validates email and password, then returns a JWT for protected endpoints.",
    responses={401: UNAUTHORIZED_RESPONSE, 422: VALIDATION_ERROR_RESPONSE},
)
async def login(payload: LoginRequest, db: DbSession) -> Token:
    user = await get_user_by_email(db, payload.email)
    if user is None or not verify_password(payload.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return Token(access_token=create_access_token(subject=str(user.id)))
