from decimal import Decimal

from fastapi import APIRouter, HTTPException, status

from app.api.deps import DbSession
from app.api.openapi import (
    CONFLICT_RESPONSE,
    NOT_FOUND_RESPONSE,
    UNAUTHORIZED_RESPONSE,
    VALIDATION_ERROR_RESPONSE,
)
from app.core.config import settings
from app.models.payment import Payment
from app.schemas.webhook import PaymentWebhookRequest, PaymentWebhookResponse
from app.services.webhook import (
    create_account,
    create_payment_and_credit,
    get_account as get_account,
    get_payment_by_transaction_id,
    get_user_by_id,
    verify_signature,
)

router = APIRouter(prefix="/webhooks", tags=["Webhooks"])


async def _already_processed_response(db: DbSession, payment: Payment) -> PaymentWebhookResponse:
    account = await get_account(db, payment.account_id)
    return PaymentWebhookResponse(
        status="already_processed",
        transaction_id=payment.transaction_id,
        account_id=payment.account_id,
        balance=account.balance if account is not None else Decimal(0),
    )


@router.post(
    "/payment",
    response_model=PaymentWebhookResponse,
    summary="Process a signed payment callback",
    description=(
        "Credits a user's account after verifying the provider's SHA-256 signature. "
        "Build the lowercase hexadecimal digest from "
        "`{account_id}{amount}{transaction_id}{user_id}{SECRET_KEY}` with no separators. "
        "The operation is idempotent: repeating a known `transaction_id` returns "
        "`already_processed` and does not credit the account again."
    ),
    responses={
        401: UNAUTHORIZED_RESPONSE,
        404: NOT_FOUND_RESPONSE,
        409: CONFLICT_RESPONSE,
        422: VALIDATION_ERROR_RESPONSE,
    },
)
async def payment_webhook(payload: PaymentWebhookRequest, db: DbSession) -> PaymentWebhookResponse:
    if not verify_signature(payload, settings.SECRET_KEY):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid signature")

    if await get_user_by_id(db, payload.user_id) is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    existing_payment = await get_payment_by_transaction_id(db, payload.transaction_id)
    if existing_payment is not None:
        return await _already_processed_response(db, existing_payment)

    account = await get_account(db, payload.account_id)
    if account is None:
        account = await create_account(db, payload.account_id, payload.user_id)
        if account is None:
            account = await get_account(db, payload.account_id)
            assert account is not None

    if account.user_id != payload.user_id:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail="Account belongs to another user"
        )

    payment = await create_payment_and_credit(
        db,
        transaction_id=payload.transaction_id,
        account_id=payload.account_id,
        user_id=payload.user_id,
        amount=payload.amount,
    )
    if payment is None:
        existing_payment = await get_payment_by_transaction_id(db, payload.transaction_id)
        assert existing_payment is not None
        return await _already_processed_response(db, existing_payment)

    await db.refresh(account)
    return PaymentWebhookResponse(
        status="processed",
        transaction_id=payment.transaction_id,
        account_id=payment.account_id,
        balance=account.balance,
    )
