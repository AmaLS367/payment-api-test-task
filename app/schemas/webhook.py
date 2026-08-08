import uuid
from decimal import Decimal
from typing import Annotated, Literal

from pydantic import BaseModel, Field


class PaymentWebhookRequest(BaseModel):
    transaction_id: uuid.UUID
    account_id: int
    user_id: int
    amount: Annotated[Decimal, Field(gt=0, max_digits=18, decimal_places=2)]
    signature: str


class PaymentWebhookResponse(BaseModel):
    status: Literal["processed", "already_processed"]
    transaction_id: uuid.UUID
    account_id: int
    balance: Decimal
