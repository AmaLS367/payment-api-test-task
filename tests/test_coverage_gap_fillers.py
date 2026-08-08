import uuid
from decimal import Decimal
from unittest.mock import patch

import pytest
from fastapi import HTTPException
from fastapi.security import HTTPAuthorizationCredentials
from httpx import AsyncClient
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.core.security import create_access_token
from app.db.session import get_db
from app.models.payment import Payment
from app.models.user import User
from app.schemas.admin import AdminUserUpdate
from app.services.account import get_accounts_by_user_id
from app.services.payment import get_payments_by_user_id
from app.services.user import update_user
from app.services.webhook import create_account, create_payment_and_credit

SEEDED_USER_ID = 1
SEEDED_ADMIN_ID = 2


def auth_headers(user_id: int) -> dict[str, str]:
    return {"Authorization": f"Bearer {create_access_token(subject=str(user_id))}"}


def bearer_credentials(token: str) -> HTTPAuthorizationCredentials:
    return HTTPAuthorizationCredentials(scheme="Bearer", credentials=token)


async def test_get_db_session_rollback_on_exception() -> None:
    """Test get_db rollback when an exception occurs inside context."""
    db_gen = get_db()
    session = await anext(db_gen)
    assert session is not None
    with pytest.raises(RuntimeError, match="DB Exception"):
        try:
            raise RuntimeError("DB Exception")
        finally:
            await db_gen.athrow(RuntimeError("DB Exception"))


async def test_update_user_service_with_and_without_password(
    db_session: AsyncSession,
) -> None:
    """Test update_user service function for password and non-password updates."""
    unique_email = f"service-update-{uuid.uuid4().hex[:8]}@example.com"
    user = User(
        email=unique_email,
        full_name="Original Name",
        hashed_password="oldhash",
        is_admin=False,
    )
    db_session.add(user)
    await db_session.flush()

    # Update without password
    update_data = AdminUserUpdate(full_name="Updated Name")
    updated = await update_user(db_session, user, update_data)
    assert updated.full_name == "Updated Name"
    assert updated.hashed_password == "oldhash"

    # Update with password
    update_data_pw = AdminUserUpdate(password="newsecretpassword")
    updated_pw = await update_user(db_session, user, update_data_pw)
    assert updated_pw.hashed_password != "oldhash"


async def test_admin_update_user_same_email(client: AsyncClient, db_session: AsyncSession) -> None:
    """Test admin update user endpoint when payload.email == user.email."""
    unique_email = f"same-email-{uuid.uuid4().hex[:8]}@example.com"
    user = User(
        email=unique_email,
        full_name="Same Email User",
        hashed_password="hash",
        is_admin=False,
    )
    db_session.add(user)
    await db_session.flush()

    response = await client.patch(
        f"/api/v1/admin/users/{user.id}",
        json={"email": unique_email, "full_name": "Updated Same Email User"},
        headers=auth_headers(SEEDED_ADMIN_ID),
    )
    assert response.status_code == 200
    assert response.json()["full_name"] == "Updated Same Email User"


async def test_admin_update_user_no_email(client: AsyncClient, db_session: AsyncSession) -> None:
    """Test admin update user endpoint when payload.email is None."""
    unique_email = f"no-email-{uuid.uuid4().hex[:8]}@example.com"
    user = User(
        email=unique_email,
        full_name="No Email User",
        hashed_password="hash",
        is_admin=False,
    )
    db_session.add(user)
    await db_session.flush()

    response = await client.patch(
        f"/api/v1/admin/users/{user.id}",
        json={"full_name": "Just Name Updated"},
        headers=auth_headers(SEEDED_ADMIN_ID),
    )
    assert response.status_code == 200
    assert response.json()["full_name"] == "Just Name Updated"


async def test_webhook_already_processed_when_account_deleted(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    """Test webhook already processed logic when payment exists but account does not."""
    transaction_id = uuid.uuid4()
    account_id = 888_888

    mock_payment = Payment(
        transaction_id=transaction_id,
        account_id=account_id,
        user_id=SEEDED_USER_ID,
        amount=Decimal("10.00"),
    )

    payload = {
        "transaction_id": str(transaction_id),
        "account_id": account_id,
        "user_id": SEEDED_USER_ID,
        "amount": "10.00",
        "signature": "ignored",
    }

    with (
        patch("app.api.routes.webhooks.verify_signature", return_value=True),
        patch("app.api.routes.webhooks.get_user_by_id", return_value=User(id=SEEDED_USER_ID)),
        patch("app.api.routes.webhooks.get_payment_by_transaction_id", return_value=mock_payment),
        patch("app.api.routes.webhooks.get_account", return_value=None),
    ):
        response = await client.post("/api/v1/webhooks/payment", json=payload)

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "already_processed"
    assert body["balance"] == "0"


async def test_create_payment_and_credit_integrity_error_re_raised(
    db_session: AsyncSession,
) -> None:
    """Test create_payment_and_credit raises IntegrityError when payment does not exist."""
    transaction_id = uuid.uuid4()

    with (
        patch.object(
            db_session,
            "begin_nested",
            side_effect=IntegrityError("stmt", {}, Exception("mock error")),
        ),
        pytest.raises(IntegrityError),
    ):
        await create_payment_and_credit(
            db_session,
            transaction_id=transaction_id,
            account_id=1,
            user_id=1,
            amount=Decimal("10.00"),
        )


async def test_get_current_user_non_existent_id_raises_401(
    db_session: AsyncSession,
) -> None:
    """Test get_current_user with valid JWT but non-existent user_id raises 401."""
    token = create_access_token(subject="999999")
    with pytest.raises(HTTPException) as exc_info:
        await get_current_user(db=db_session, token=bearer_credentials(token))
    assert exc_info.value.status_code == 401


async def test_get_accounts_and_payments_empty_for_user(
    db_session: AsyncSession,
) -> None:
    """Test get_accounts_by_user_id and get_payments_by_user_id when user has no records."""
    accounts = await get_accounts_by_user_id(db_session, 999999)
    assert len(accounts) == 0

    payments = await get_payments_by_user_id(db_session, 999999)
    assert len(payments) == 0


async def test_create_account_integrity_error_returns_none(
    db_session: AsyncSession,
) -> None:
    """Test create_account returns None when IntegrityError is caught."""
    with patch.object(
        db_session, "begin_nested", side_effect=IntegrityError("stmt", {}, Exception("mock error"))
    ):
        res = await create_account(db_session, account_id=100, user_id=1)
        assert res is None
