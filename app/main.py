from fastapi import FastAPI

from app.api.routes import api_router
from app.core.config import settings

app = FastAPI(
    title="Payment API",
    description="Secure payment account API with JWT-protected user and admin endpoints.",
    version="0.1.0",
    openapi_tags=[
        {"name": "Auth", "description": "Obtain access tokens for protected endpoints."},
        {"name": "Users", "description": "View the authenticated user's profile and payment data."},
        {"name": "Admin", "description": "Manage regular users. Administrator access is required."},
        {
            "name": "Webhooks",
            "description": "Receive signed payment-provider callbacks and credit accounts.",
        },
    ],
)

app.include_router(api_router, prefix=settings.API_V1_PREFIX)


@app.get(
    "/health",
    summary="Check API health",
    description="Returns a lightweight status response for uptime checks.",
)
async def health() -> dict[str, str]:
    return {"status": "ok"}
