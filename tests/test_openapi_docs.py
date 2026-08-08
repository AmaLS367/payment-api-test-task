from app.main import app


def test_openapi_documents_the_public_api() -> None:
    schema = app.openapi()

    assert schema["info"] == {
        "title": "Payment API",
        "description": "Secure payment account API with JWT-protected user and admin endpoints.",
        "version": "0.1.0",
    }
    assert {tag["name"] for tag in schema["tags"]} == {"Auth", "Users", "Admin", "Webhooks"}

    for path in schema["paths"].values():
        for operation in path.values():
            assert operation["summary"]
            assert operation["description"]

    assert schema["components"]["securitySchemes"]["HTTPBearer"]["scheme"] == "bearer"
    assert schema["paths"]["/api/v1/users/me"]["get"]["security"] == [{"HTTPBearer": []}]
    assert "401" in schema["paths"]["/api/v1/auth/login"]["post"]["responses"]
    assert "409" in schema["paths"]["/api/v1/admin/users"]["post"]["responses"]


def test_openapi_documents_payment_webhook_contract() -> None:
    schema = app.openapi()
    operation = schema["paths"]["/api/v1/webhooks/payment"]["post"]
    request_schema = schema["components"]["schemas"]["PaymentWebhookRequest"]

    assert "idempotent" in operation["description"].lower()
    assert "SHA-256" in operation["description"]
    assert request_schema["required"] == [
        "transaction_id",
        "account_id",
        "user_id",
        "amount",
        "signature",
    ]
    assert request_schema["examples"]
    assert {"401", "404", "409", "422"}.issubset(operation["responses"])
