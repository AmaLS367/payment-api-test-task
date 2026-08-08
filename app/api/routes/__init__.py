from fastapi import APIRouter

from app.api.routes import admin, auth, users, webhooks

api_router = APIRouter()
api_router.include_router(auth.router)
api_router.include_router(users.router)
api_router.include_router(admin.router)
api_router.include_router(webhooks.router)
