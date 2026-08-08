import asyncio
import hashlib
import uuid
from decimal import Decimal
from unittest.mock import patch

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import delete, insert, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.routes import webhooks as webhooks_module
from app.core.config import settings
from app.main import app
from app.models.account import Account
from app.models.payment import Payment
from app.models.user import User

SEEDED_USER_ID = 1
SEEDED_ACCOUNT_ID = 1
UNKNOWN_USER_ID = 999_999


def unique_account_id() -> int:
    return uuid.uuid4().int % 900_000 + 100_000


def build_signature(
    *, account_id: int, amount: Decimal, transaction_id: uuid.UUID, user_id: int
) -> str:
    raw = f"{account_id}{amount}{transaction_id}{user_id}{settings.SECRET_KEY}"
    return hashlib.sha256(raw.encode()).hexdigest()


def build_payload(
    *, account_id: int, amount: Decimal, transaction_id: uuid.UUID, user_id: int
) -> dict:
    return {
        "transaction_id": str(transaction_id),
        "account_id": account_id,
        "user_id": user_id,
        "amount": str(amount),
        "signature": build_signature(
            account_id=account_id, amount=amount, transaction_id=transaction_id, user_id=user_id
        ),
    }


@pytest.fixture
async def other_user(db_session: AsyncSession) -> User:
    unique = uuid.uuid4().hex[:12]
    user = User(
        email=f"other-{unique}@example.com",
        full_name="Other User",
        hashed_password="irrelevant-hash",
        is_admin=False,
    )
    db_session.add(user)
    await db_session.flush()
    return user


@pytest.fixture
async def other_user_account(db_session: AsyncSession, other_user: User) -> Account:
    account = Account(id=unique_account_id(), user_id=other_user.id, balance=Decimal("500.00"))
    db_session.add(account)
    await db_session.flush()
    return account


async def test_payment_webhook_success_existing_account(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    transaction_id = uuid.uuid4()
    amount = Decimal("100.00")
    payload = build_payload(
        account_id=SEEDED_ACCOUNT_ID,
        amount=amount,
        transaction_id=transaction_id,
        user_id=SEEDED_USER_ID,
    )

    response = await client.post("/api/v1/webhooks/payment", json=payload)

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "processed"
    assert body["account_id"] == SEEDED_ACCOUNT_ID
    assert Decimal(body["balance"]) == amount

    result = await db_session.execute(
        select(Payment).where(Payment.transaction_id == transaction_id)
    )
    payment = result.scalar_one()
    assert payment.account_id == SEEDED_ACCOUNT_ID
    assert payment.user_id == SEEDED_USER_ID
    assert payment.amount == amount

    account = await db_session.get(Account, SEEDED_ACCOUNT_ID)
    assert account is not None
    assert account.balance == amount


async def test_payment_webhook_creates_account_when_missing(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    account_id = unique_account_id()
    transaction_id = uuid.uuid4()
    amount = Decimal("50.00")
    payload = build_payload(
        account_id=account_id, amount=amount, transaction_id=transaction_id, user_id=SEEDED_USER_ID
    )

    response = await client.post("/api/v1/webhooks/payment", json=payload)

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "processed"
    assert Decimal(body["balance"]) == amount

    account = await db_session.get(Account, account_id)
    assert account is not None
    assert account.user_id == SEEDED_USER_ID
    assert account.balance == amount


async def test_payment_webhook_invalid_signature_returns_401(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    transaction_id = uuid.uuid4()
    payload = build_payload(
        account_id=SEEDED_ACCOUNT_ID,
        amount=Decimal("10.00"),
        transaction_id=transaction_id,
        user_id=SEEDED_USER_ID,
    )
    payload["signature"] = "0" * 64

    response = await client.post("/api/v1/webhooks/payment", json=payload)

    assert response.status_code == 401

    result = await db_session.execute(
        select(Payment).where(Payment.transaction_id == transaction_id)
    )
    assert result.scalar_one_or_none() is None

    account = await db_session.get(Account, SEEDED_ACCOUNT_ID)
    assert account is not None
    assert account.balance == Decimal("0.00")


async def test_payment_webhook_duplicate_transaction_id_returns_already_processed(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    account_id = unique_account_id()
    transaction_id = uuid.uuid4()
    amount = Decimal("75.00")
    payload = build_payload(
        account_id=account_id, amount=amount, transaction_id=transaction_id, user_id=SEEDED_USER_ID
    )

    first = await client.post("/api/v1/webhooks/payment", json=payload)
    assert first.status_code == 200
    assert first.json()["status"] == "processed"

    second = await client.post("/api/v1/webhooks/payment", json=payload)
    assert second.status_code == 200
    body = second.json()
    assert body["status"] == "already_processed"
    assert Decimal(body["balance"]) == amount

    result = await db_session.execute(
        select(Payment).where(Payment.transaction_id == transaction_id)
    )
    payments = result.scalars().all()
    assert len(payments) == 1

    account = await db_session.get(Account, account_id)
    assert account is not None
    assert account.balance == amount


async def test_payment_webhook_account_belongs_to_another_user_returns_409(
    client: AsyncClient, db_session: AsyncSession, other_user_account: Account
) -> None:
    transaction_id = uuid.uuid4()
    payload = build_payload(
        account_id=other_user_account.id,
        amount=Decimal("25.00"),
        transaction_id=transaction_id,
        user_id=SEEDED_USER_ID,
    )

    response = await client.post("/api/v1/webhooks/payment", json=payload)

    assert response.status_code == 409

    result = await db_session.execute(
        select(Payment).where(Payment.transaction_id == transaction_id)
    )
    assert result.scalar_one_or_none() is None

    await db_session.refresh(other_user_account)
    assert other_user_account.balance == Decimal("500.00")


async def test_payment_webhook_amount_with_too_many_decimals_returns_422(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    account_id = unique_account_id()
    transaction_id = uuid.uuid4()
    payload = build_payload(
        account_id=account_id,
        amount=Decimal("0.001"),
        transaction_id=transaction_id,
        user_id=SEEDED_USER_ID,
    )

    response = await client.post("/api/v1/webhooks/payment", json=payload)

    assert response.status_code == 422

    result = await db_session.execute(
        select(Payment).where(Payment.transaction_id == transaction_id)
    )
    assert result.scalar_one_or_none() is None
    assert await db_session.get(Account, account_id) is None


async def test_payment_webhook_concurrent_duplicate_transaction_id_credits_once(
    db_session: AsyncSession,
) -> None:
    """Two genuinely independent requests (each with its own DB session, not the
    shared rollback-isolated `db_session`/`client` fixtures) race on the same
    transaction_id. Exactly one must be credited; the loser must see a real,
    committed duplicate rather than have the error masked.
    """
    account_id = unique_account_id()
    transaction_id = uuid.uuid4()
    amount = Decimal("40.00")

    account = Account(id=account_id, user_id=SEEDED_USER_ID, balance=Decimal("0.00"))
    db_session.add(account)
    await db_session.commit()

    payload = build_payload(
        account_id=account_id, amount=amount, transaction_id=transaction_id, user_id=SEEDED_USER_ID
    )

    async def post_webhook():
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as ac:
            return await ac.post("/api/v1/webhooks/payment", json=payload)

    try:
        first, second = await asyncio.gather(post_webhook(), post_webhook())

        assert first.status_code == 200
        assert second.status_code == 200
        statuses = sorted([first.json()["status"], second.json()["status"]])
        assert statuses == ["already_processed", "processed"]

        result = await db_session.execute(
            select(Payment).where(Payment.transaction_id == transaction_id)
        )
        assert len(result.scalars().all()) == 1

        balance_result = await db_session.execute(
            select(Account.balance).where(Account.id == account_id)
        )
        assert balance_result.scalar_one() == amount
    finally:
        await db_session.execute(delete(Payment).where(Payment.transaction_id == transaction_id))
        await db_session.execute(delete(Account).where(Account.id == account_id))
        await db_session.commit()


async def test_payment_webhook_account_creation_race_returns_409(
    client: AsyncClient, db_session: AsyncSession, other_user: User
) -> None:
    """If a concurrent request creates account_id for a different user between our
    initial lookup and our create attempt, we must re-check ownership on the
    re-fetched account instead of blindly crediting it.

    The competing row is inserted via Core `insert()` (not the ORM) so it never
    enters this session's identity map — mirroring how a real concurrent request's
    own session would create it, and avoiding a spurious identity-map conflict when
    create_account() later builds its own Account(id=...) instance for the same PK.
    """
    account_id = unique_account_id()
    other_balance = Decimal("500.00")
    await db_session.execute(
        insert(Account).values(id=account_id, user_id=other_user.id, balance=other_balance)
    )
    await db_session.flush()

    transaction_id = uuid.uuid4()
    payload = build_payload(
        account_id=account_id,
        amount=Decimal("30.00"),
        transaction_id=transaction_id,
        user_id=SEEDED_USER_ID,
    )

    real_get_account = webhooks_module.get_account
    call_count = 0

    async def flaky_get_account(db: AsyncSession, account_id: int) -> Account | None:
        nonlocal call_count
        call_count += 1
        if call_count == 1:
            return None
        return await real_get_account(db, account_id)

    with patch.object(webhooks_module, "get_account", side_effect=flaky_get_account):
        response = await client.post("/api/v1/webhooks/payment", json=payload)

    assert response.status_code == 409
    assert call_count == 2

    result = await db_session.execute(
        select(Payment).where(Payment.transaction_id == transaction_id)
    )
    assert result.scalar_one_or_none() is None

    balance_result = await db_session.execute(
        select(Account.balance).where(Account.id == account_id)
    )
    assert balance_result.scalar_one() == other_balance


async def test_payment_webhook_unknown_user_returns_404(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    account_id = unique_account_id()
    transaction_id = uuid.uuid4()
    payload = build_payload(
        account_id=account_id,
        amount=Decimal("15.00"),
        transaction_id=transaction_id,
        user_id=UNKNOWN_USER_ID,
    )

    response = await client.post("/api/v1/webhooks/payment", json=payload)

    assert response.status_code == 404

    result = await db_session.execute(
        select(Payment).where(Payment.transaction_id == transaction_id)
    )
    assert result.scalar_one_or_none() is None

    account = await db_session.get(Account, account_id)
    assert account is None
