from typing import Any

from fastapi import APIRouter, HTTPException, status

from app.api.deps import CurrentAdmin, DbSession
from app.api.openapi import (
    CONFLICT_RESPONSE,
    FORBIDDEN_RESPONSE,
    NOT_FOUND_RESPONSE,
    UNAUTHORIZED_RESPONSE,
    VALIDATION_ERROR_RESPONSE,
)
from app.schemas.admin import AdminUserCreate, AdminUserUpdate, AdminUserWithAccountsRead
from app.schemas.user import UserRead
from app.services.user import (
    create_user,
    delete_user,
    get_regular_user_by_id,
    get_regular_users_with_accounts,
    get_user_by_email,
    update_user,
)

router = APIRouter(prefix="/admin", tags=["Admin"])

ADMIN_ACCESS_RESPONSES: dict[int | str, dict[str, Any]] = {
    401: UNAUTHORIZED_RESPONSE,
    403: FORBIDDEN_RESPONSE,
}


@router.get(
    "/me",
    response_model=UserRead,
    summary="Get the current administrator",
    description="Returns the profile for the authenticated administrator.",
    responses=ADMIN_ACCESS_RESPONSES,
)
async def read_admin_me(current_admin: CurrentAdmin) -> UserRead:
    return UserRead.model_validate(current_admin)


@router.get(
    "/users",
    response_model=list[AdminUserWithAccountsRead],
    summary="List regular users",
    description="Returns every non-administrator user together with their accounts.",
    responses=ADMIN_ACCESS_RESPONSES,
)
async def list_users(current_admin: CurrentAdmin, db: DbSession) -> list[AdminUserWithAccountsRead]:
    users = await get_regular_users_with_accounts(db)
    return [AdminUserWithAccountsRead.model_validate(u) for u in users]


@router.post(
    "/users",
    response_model=UserRead,
    status_code=status.HTTP_201_CREATED,
    summary="Create a regular user",
    description="Creates a non-administrator user. Email addresses must be unique.",
    responses={
        **ADMIN_ACCESS_RESPONSES,
        409: CONFLICT_RESPONSE,
        422: VALIDATION_ERROR_RESPONSE,
    },
)
async def create_admin_user(
    payload: AdminUserCreate, current_admin: CurrentAdmin, db: DbSession
) -> UserRead:
    if await get_user_by_email(db, payload.email) is not None:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Email already registered")
    created_user = await create_user(db, payload)
    return UserRead.model_validate(created_user)


@router.patch(
    "/users/{user_id}",
    response_model=UserRead,
    summary="Update a regular user",
    description="Updates supplied profile fields for a non-administrator user.",
    responses={
        **ADMIN_ACCESS_RESPONSES,
        404: NOT_FOUND_RESPONSE,
        409: CONFLICT_RESPONSE,
        422: VALIDATION_ERROR_RESPONSE,
    },
)
async def update_admin_user(
    user_id: int, payload: AdminUserUpdate, current_admin: CurrentAdmin, db: DbSession
) -> UserRead:
    user = await get_regular_user_by_id(db, user_id)
    if user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    if (
        payload.email is not None
        and payload.email != user.email
        and await get_user_by_email(db, payload.email) is not None
    ):
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Email already registered")
    updated_user = await update_user(db, user, payload)
    return UserRead.model_validate(updated_user)


@router.delete(
    "/users/{user_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a regular user",
    description="Permanently deletes a non-administrator user and their associated records.",
    responses={**ADMIN_ACCESS_RESPONSES, 404: NOT_FOUND_RESPONSE, 422: VALIDATION_ERROR_RESPONSE},
)
async def delete_admin_user(user_id: int, current_admin: CurrentAdmin, db: DbSession) -> None:
    user = await get_regular_user_by_id(db, user_id)
    if user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    await delete_user(db, user)
