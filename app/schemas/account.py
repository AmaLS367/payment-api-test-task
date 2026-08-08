from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field


class AccountRead(BaseModel):
    model_config = ConfigDict(
        from_attributes=True,
        json_schema_extra={"examples": [{"id": 1, "balance": "150.00"}]},
    )

    id: int = Field(description="Account identifier.")
    balance: Decimal = Field(description="Current account balance.")
