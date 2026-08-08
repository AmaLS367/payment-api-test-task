from datetime import timedelta

import pytest
from fastapi import HTTPException
from fastapi.security import HTTPAuthorizationCredentials
from httpx import AsyncClient
from jose import jwt
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.core.config import settings
from app.core.security import create_access_token


def bearer_credentials(token: str) -> HTTPAuthorizationCredentials:
    return HTTPAuthorizationCredentials(scheme="Bearer", credentials=token)


async def test_login_success_returns_token_for_seeded_user(client: AsyncClient) -> None:
    response = await client.post(
        "/api/v1/auth/login", json={"email": "user@example.com", "password": "user-password"}
    )
    assert response.status_code == 200
    body = response.json()
    assert body["token_type"] == "bearer"
    payload = jwt.decode(
        body["access_token"], settings.JWT_SECRET_KEY, algorithms=[settings.JWT_ALGORITHM]
    )
    assert payload["sub"] == "1"


async def test_login_success_returns_token_for_seeded_admin(client: AsyncClient) -> None:
    response = await client.post(
        "/api/v1/auth/login", json={"email": "admin@example.com", "password": "admin-password"}
    )
    assert response.status_code == 200
    body = response.json()
    assert body["token_type"] == "bearer"
    payload = jwt.decode(
        body["access_token"], settings.JWT_SECRET_KEY, algorithms=[settings.JWT_ALGORITHM]
    )
    assert payload["sub"] == "2"

    me_response = await client.get(
        "/api/v1/admin/me", headers={"Authorization": f"Bearer {body['access_token']}"}
    )
    assert me_response.status_code == 200
    assert me_response.json() == {
        "id": 2,
        "email": "admin@example.com",
        "full_name": "Test Admin",
    }


async def test_login_wrong_password_returns_401(client: AsyncClient) -> None:
    response = await client.post(
        "/api/v1/auth/login", json={"email": "user@example.com", "password": "wrong-password"}
    )
    assert response.status_code == 401


async def test_login_unknown_email_returns_401(client: AsyncClient) -> None:
    response = await client.post(
        "/api/v1/auth/login", json={"email": "nobody@example.com", "password": "whatever"}
    )
    assert response.status_code == 401


async def test_get_current_user_with_valid_token_returns_user(db_session: AsyncSession) -> None:
    token = create_access_token(subject="2")
    user = await get_current_user(db=db_session, token=bearer_credentials(token))
    assert user.id == 2
    assert user.email == "admin@example.com"


async def test_get_current_user_with_invalid_token_raises_401(db_session: AsyncSession) -> None:
    with pytest.raises(HTTPException) as exc_info:
        await get_current_user(db=db_session, token=bearer_credentials("not-a-real-jwt"))
    assert exc_info.value.status_code == 401


async def test_get_current_user_with_expired_token_raises_401(db_session: AsyncSession) -> None:
    token = create_access_token(subject="1", expires_delta=timedelta(minutes=-5))
    with pytest.raises(HTTPException) as exc_info:
        await get_current_user(db=db_session, token=bearer_credentials(token))
    assert exc_info.value.status_code == 401
