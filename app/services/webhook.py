import hashlib
import hmac
import uuid
from decimal import Decimal

from sqlalchemy import select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.account import Account
from app.models.payment import Payment
from app.models.user import User
from app.schemas.webhook import PaymentWebhookRequest


def verify_signature(payload: PaymentWebhookRequest, secret: str) -> bool:
    raw = f"{payload.account_id}{payload.amount}{payload.transaction_id}{payload.user_id}{secret}"
    expected = hashlib.sha256(raw.encode()).hexdigest()
    return hmac.compare_digest(expected, payload.signature)


async def get_user_by_id(db: AsyncSession, user_id: int) -> User | None:
    result = await db.execute(select(User).where(User.id == user_id))
    return result.scalar_one_or_none()


async def get_payment_by_transaction_id(
    db: AsyncSession, transaction_id: uuid.UUID
) -> Payment | None:
    result = await db.execute(select(Payment).where(Payment.transaction_id == transaction_id))
    return result.scalar_one_or_none()


async def get_account(db: AsyncSession, account_id: int) -> Account | None:
    result = await db.execute(select(Account).where(Account.id == account_id))
    return result.scalar_one_or_none()


async def create_account(db: AsyncSession, account_id: int, user_id: int) -> Account | None:
    account = Account(id=account_id, user_id=user_id, balance=Decimal(0))
    try:
        async with db.begin_nested():
            db.add(account)
            await db.flush()
    except IntegrityError:
        return None
    return account


async def create_payment_and_credit(
    db: AsyncSession,
    *,
    transaction_id: uuid.UUID,
    account_id: int,
    user_id: int,
    amount: Decimal,
) -> Payment | None:
    payment = Payment(
        transaction_id=transaction_id,
        account_id=account_id,
        user_id=user_id,
        amount=amount,
    )
    try:
        async with db.begin_nested():
            db.add(payment)
            await db.execute(
                update(Account)
                .where(Account.id == account_id)
                .values(balance=Account.balance + amount)
            )
            await db.flush()
    except IntegrityError:
        return None
    return payment
