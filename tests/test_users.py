import uuid
from decimal import Decimal

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import create_access_token, get_password_hash
from app.models.account import Account
from app.models.payment import Payment
from app.models.user import User

SEEDED_USER_ID = 1
SEEDED_USER_EMAIL = "user@example.com"
SEEDED_USER_FULL_NAME = "Test User"
SEEDED_ACCOUNT_ID = 1


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


@pytest.fixture
async def other_user_payment(db_session: AsyncSession, other_user_account: Account) -> Payment:
    payment = Payment(
        transaction_id=uuid.uuid4(),
        account_id=other_user_account.id,
        user_id=other_user_account.user_id,
        amount=Decimal("25.00"),
    )
    db_session.add(payment)
    await db_session.flush()
    return payment


@pytest.fixture
async def seeded_user_payment(db_session: AsyncSession) -> Payment:
    payment = Payment(
        transaction_id=uuid.uuid4(),
        account_id=SEEDED_ACCOUNT_ID,
        user_id=SEEDED_USER_ID,
        amount=Decimal("10.00"),
    )
    db_session.add(payment)
    await db_session.flush()
    return payment


async def test_me_requires_auth_returns_401(client: AsyncClient) -> None:
    response = await client.get("/api/v1/users/me")
    assert response.status_code == 401


async def test_accounts_requires_auth_returns_401(client: AsyncClient) -> None:
    response = await client.get("/api/v1/users/me/accounts")
    assert response.status_code == 401


async def test_payments_requires_auth_returns_401(client: AsyncClient) -> None:
    response = await client.get("/api/v1/users/me/payments")
    assert response.status_code == 401


async def test_me_returns_authenticated_users_own_data(client: AsyncClient) -> None:
    response = await client.get("/api/v1/users/me", headers=auth_headers(SEEDED_USER_ID))
    assert response.status_code == 200
    assert response.json() == {
        "id": SEEDED_USER_ID,
        "email": SEEDED_USER_EMAIL,
        "full_name": SEEDED_USER_FULL_NAME,
    }


async def test_me_returns_other_users_own_data(client: AsyncClient, other_user: User) -> None:
    response = await client.get("/api/v1/users/me", headers=auth_headers(other_user.id))
    assert response.status_code == 200
    body = response.json()
    assert body["id"] == other_user.id
    assert body["email"] == other_user.email
    assert body["full_name"] == other_user.full_name


async def test_accounts_returns_only_own_accounts(
    client: AsyncClient, other_user_account: Account
) -> None:
    response = await client.get(
        "/api/v1/users/me/accounts", headers=auth_headers(SEEDED_USER_ID)
    )
    assert response.status_code == 200
    ids = {item["id"] for item in response.json()}
    assert SEEDED_ACCOUNT_ID in ids
    assert other_user_account.id not in ids


async def test_accounts_isolated_for_other_user(
    client: AsyncClient, other_user_account: Account
) -> None:
    response = await client.get(
        "/api/v1/users/me/accounts", headers=auth_headers(other_user_account.user_id)
    )
    assert response.status_code == 200
    ids = {item["id"] for item in response.json()}
    assert ids == {other_user_account.id}


async def test_payments_returns_only_own_payments(
    client: AsyncClient, seeded_user_payment: Payment, other_user_payment: Payment
) -> None:
    response = await client.get(
        "/api/v1/users/me/payments", headers=auth_headers(SEEDED_USER_ID)
    )
    assert response.status_code == 200
    transaction_ids = {item["transaction_id"] for item in response.json()}
    assert str(seeded_user_payment.transaction_id) in transaction_ids
    assert str(other_user_payment.transaction_id) not in transaction_ids


async def test_payments_isolated_for_other_user(
    client: AsyncClient, seeded_user_payment: Payment, other_user_payment: Payment
) -> None:
    response = await client.get(
        "/api/v1/users/me/payments", headers=auth_headers(other_user_payment.user_id)
    )
    assert response.status_code == 200
    transaction_ids = {item["transaction_id"] for item in response.json()}
    assert transaction_ids == {str(other_user_payment.transaction_id)}
