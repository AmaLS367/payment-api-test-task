import uuid
from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field


class PaymentRead(BaseModel):
    model_config = ConfigDict(
        from_attributes=True,
        json_schema_extra={
            "examples": [
                {
                    "transaction_id": "550e8400-e29b-41d4-a716-446655440000",
                    "account_id": 1,
                    "amount": "100.00",
                    "created_at": "2026-08-08T12:00:00Z",
                }
            ]
        },
    )

    transaction_id: uuid.UUID = Field(description="Provider transaction identifier.")
    account_id: int = Field(description="Credited account identifier.")
    amount: Decimal = Field(description="Payment amount credited to the account.")
    created_at: datetime = Field(description="Timestamp when the payment was recorded.")
