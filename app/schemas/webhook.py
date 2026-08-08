import uuid
from decimal import Decimal
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field


class PaymentWebhookRequest(BaseModel):
    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {
                    "transaction_id": "550e8400-e29b-41d4-a716-446655440000",
                    "account_id": 1,
                    "user_id": 1,
                    "amount": "100.00",
                    "signature": "8df52484d653bbeb2b5ce4d138c42e5fb9d5af804827c5bcff0bf351ca0446ce",
                }
            ]
        }
    )

    transaction_id: uuid.UUID = Field(description="Unique provider transaction identifier.")
    account_id: int = Field(description="Account identifier to credit.")
    user_id: int = Field(description="Owner of the account receiving the payment.")
    amount: Annotated[
        Decimal,
        Field(
            gt=0,
            max_digits=18,
            decimal_places=2,
            description="Positive payment amount with no more than two decimal places.",
        ),
    ]
    signature: str = Field(
        description=(
            "Lowercase SHA-256 hexadecimal digest of "
            "`{account_id}{amount}{transaction_id}{user_id}{SECRET_KEY}`."
        )
    )


class PaymentWebhookResponse(BaseModel):
    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {
                    "status": "processed",
                    "transaction_id": "550e8400-e29b-41d4-a716-446655440000",
                    "account_id": 1,
                    "balance": "100.00",
                },
                {
                    "status": "already_processed",
                    "transaction_id": "550e8400-e29b-41d4-a716-446655440000",
                    "account_id": 1,
                    "balance": "100.00",
                },
            ]
        }
    )

    status: Literal["processed", "already_processed"] = Field(
        description="Whether the payment was newly processed or was already recorded."
    )
    transaction_id: uuid.UUID = Field(description="Provider transaction identifier.")
    account_id: int = Field(description="Credited account identifier.")
    balance: Decimal = Field(description="Account balance after processing.")
