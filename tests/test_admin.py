import uuid
from decimal import Decimal

import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import create_access_token, get_password_hash, verify_password
from app.models.account import Account
from app.models.user import User

SEEDED_USER_ID = 1
SEEDED_USER_EMAIL = "user@example.com"
SEEDED_ADMIN_ID = 2
SEEDED_ADMIN_EMAIL = "admin@example.com"
SEEDED_ADMIN_FULL_NAME = "Test Admin"


def auth_headers(user_id: int) -> dict[str, str]:
    return {"Authorization": f"Bearer {create_access_token(subject=str(user_id))}"}


@pytest.fixture
async def other_user(db_session: AsyncSession) -> User:
    unique = uuid.uuid4().hex[:12]
    user = User(
        email=f"other-{unique}@example.com",
        full_name="Other User",
        hashed_password=get_password_hash("other-password"),
        is_admin=False,
    )
    db_session.add(user)
    await db_session.flush()
    return user


@pytest.fixture
async def other_user_account(db_session: AsyncSession, other_user: User) -> Account:
    account = Account(user_id=other_user.id, balance=Decimal("500.00"))
    db_session.add(account)
    await db_session.flush()
    return account


def unique_email() -> str:
    return f"new-{uuid.uuid4().hex[:12]}@example.com"


# --- 401 / 403 ---


async def test_admin_me_requires_auth_returns_401(client: AsyncClient) -> None:
    response = await client.get("/api/v1/admin/me")
    assert response.status_code == 401


async def test_admin_me_requires_admin_returns_403(client: AsyncClient) -> None:
    response = await client.get("/api/v1/admin/me", headers=auth_headers(SEEDED_USER_ID))
    assert response.status_code == 403


async def test_list_users_requires_auth_returns_401(client: AsyncClient) -> None:
    response = await client.get("/api/v1/admin/users")
    assert response.status_code == 401


async def test_list_users_requires_admin_returns_403(client: AsyncClient) -> None:
    response = await client.get("/api/v1/admin/users", headers=auth_headers(SEEDED_USER_ID))
    assert response.status_code == 403


async def test_create_user_requires_auth_returns_401(client: AsyncClient) -> None:
    response = await client.post(
        "/api/v1/admin/users",
        json={"email": unique_email(), "full_name": "X", "password": "pw"},
    )
    assert response.status_code == 401


async def test_create_user_requires_admin_returns_403(client: AsyncClient) -> None:
    response = await client.post(
        "/api/v1/admin/users",
        json={"email": unique_email(), "full_name": "X", "password": "pw"},
        headers=auth_headers(SEEDED_USER_ID),
    )
    assert response.status_code == 403


async def test_update_user_requires_auth_returns_401(
    client: AsyncClient, other_user: User
) -> None:
    response = await client.patch(
        f"/api/v1/admin/users/{other_user.id}", json={"full_name": "New Name"}
    )
    assert response.status_code == 401


async def test_update_user_requires_admin_returns_403(
    client: AsyncClient, other_user: User
) -> None:
    response = await client.patch(
        f"/api/v1/admin/users/{other_user.id}",
        json={"full_name": "New Name"},
        headers=auth_headers(SEEDED_USER_ID),
    )
    assert response.status_code == 403


async def test_delete_user_requires_auth_returns_401(
    client: AsyncClient, other_user: User
) -> None:
    response = await client.delete(f"/api/v1/admin/users/{other_user.id}")
    assert response.status_code == 401


async def test_delete_user_requires_admin_returns_403(
    client: AsyncClient, other_user: User
) -> None:
    response = await client.delete(
        f"/api/v1/admin/users/{other_user.id}", headers=auth_headers(SEEDED_USER_ID)
    )
    assert response.status_code == 403


# --- GET /admin/me ---


async def test_admin_me_returns_current_admin(client: AsyncClient) -> None:
    response = await client.get("/api/v1/admin/me", headers=auth_headers(SEEDED_ADMIN_ID))
    assert response.status_code == 200
    assert response.json() == {
        "id": SEEDED_ADMIN_ID,
        "email": SEEDED_ADMIN_EMAIL,
        "full_name": SEEDED_ADMIN_FULL_NAME,
    }


# --- create ---


async def test_create_user_success(client: AsyncClient, db_session: AsyncSession) -> None:
    email = unique_email()
    response = await client.post(
        "/api/v1/admin/users",
        json={"email": email, "full_name": "New Person", "password": "secret-pw"},
        headers=auth_headers(SEEDED_ADMIN_ID),
    )
    assert response.status_code == 201
    body = response.json()
    assert body["email"] == email
    assert body["full_name"] == "New Person"
    assert "password" not in body
    assert "is_admin" not in body

    result = await db_session.execute(select(User).where(User.email == email))
    created = result.scalar_one()
    assert created.is_admin is False
    assert verify_password("secret-pw", created.hashed_password)


async def test_create_user_duplicate_email_returns_409(client: AsyncClient) -> None:
    response = await client.post(
        "/api/v1/admin/users",
        json={"email": SEEDED_USER_EMAIL, "full_name": "Dup", "password": "secret-pw"},
        headers=auth_headers(SEEDED_ADMIN_ID),
    )
    assert response.status_code == 409


# --- update ---


async def test_update_user_success(
    client: AsyncClient, db_session: AsyncSession, other_user: User
) -> None:
    new_email = unique_email()
    response = await client.patch(
        f"/api/v1/admin/users/{other_user.id}",
        json={"email": new_email, "full_name": "Renamed", "password": "new-secret"},
        headers=auth_headers(SEEDED_ADMIN_ID),
    )
    assert response.status_code == 200
    body = response.json()
    assert body == {"id": other_user.id, "email": new_email, "full_name": "Renamed"}

    await db_session.refresh(other_user)
    assert other_user.email == new_email
    assert other_user.full_name == "Renamed"
    assert verify_password("new-secret", other_user.hashed_password)


async def test_update_user_duplicate_email_returns_409(
    client: AsyncClient, other_user: User
) -> None:
    response = await client.patch(
        f"/api/v1/admin/users/{other_user.id}",
        json={"email": SEEDED_USER_EMAIL},
        headers=auth_headers(SEEDED_ADMIN_ID),
    )
    assert response.status_code == 409


async def test_update_user_missing_id_returns_404(client: AsyncClient) -> None:
    response = await client.patch(
        "/api/v1/admin/users/999999",
        json={"full_name": "Nobody"},
        headers=auth_headers(SEEDED_ADMIN_ID),
    )
    assert response.status_code == 404


async def test_update_admin_user_returns_404(client: AsyncClient) -> None:
    response = await client.patch(
        f"/api/v1/admin/users/{SEEDED_ADMIN_ID}",
        json={"full_name": "Hacked"},
        headers=auth_headers(SEEDED_ADMIN_ID),
    )
    assert response.status_code == 404


# --- delete ---


async def test_delete_user_success(
    client: AsyncClient, db_session: AsyncSession, other_user: User
) -> None:
    response = await client.delete(
        f"/api/v1/admin/users/{other_user.id}", headers=auth_headers(SEEDED_ADMIN_ID)
    )
    assert response.status_code == 204
    assert response.content == b""

    result = await db_session.execute(select(User).where(User.id == other_user.id))
    assert result.scalar_one_or_none() is None


async def test_delete_user_missing_id_returns_404(client: AsyncClient) -> None:
    response = await client.delete(
        "/api/v1/admin/users/999999", headers=auth_headers(SEEDED_ADMIN_ID)
    )
    assert response.status_code == 404


async def test_delete_admin_user_returns_404(client: AsyncClient) -> None:
    response = await client.delete(
        f"/api/v1/admin/users/{SEEDED_ADMIN_ID}", headers=auth_headers(SEEDED_ADMIN_ID)
    )
    assert response.status_code == 404


# --- list ---


async def test_list_users_returns_regular_users_with_accounts(
    client: AsyncClient, other_user: User, other_user_account: Account
) -> None:
    response = await client.get("/api/v1/admin/users", headers=auth_headers(SEEDED_ADMIN_ID))
    assert response.status_code == 200
    body = response.json()

    ids = {item["id"] for item in body}
    assert SEEDED_ADMIN_ID not in ids
    assert other_user.id in ids
    assert SEEDED_USER_ID in ids

    entry = next(item for item in body if item["id"] == other_user.id)
    assert entry["email"] == other_user.email
    assert entry["full_name"] == other_user.full_name
    assert entry["accounts"] == [
        {"id": other_user_account.id, "balance": str(other_user_account.balance)}
    ]
