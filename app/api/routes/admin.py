from fastapi import APIRouter, HTTPException, status

from app.api.deps import CurrentAdmin, DbSession
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

router = APIRouter(prefix="/admin", tags=["admin"])


@router.get("/me", response_model=UserRead)
async def read_admin_me(current_admin: CurrentAdmin) -> UserRead:
    return current_admin


@router.get("/users", response_model=list[AdminUserWithAccountsRead])
async def list_users(
    current_admin: CurrentAdmin, db: DbSession
) -> list[AdminUserWithAccountsRead]:
    return await get_regular_users_with_accounts(db)


@router.post("/users", response_model=UserRead, status_code=status.HTTP_201_CREATED)
async def create_admin_user(
    payload: AdminUserCreate, current_admin: CurrentAdmin, db: DbSession
) -> UserRead:
    if await get_user_by_email(db, payload.email) is not None:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Email already registered")
    return await create_user(db, payload)


@router.patch("/users/{user_id}", response_model=UserRead)
async def update_admin_user(
    user_id: int, payload: AdminUserUpdate, current_admin: CurrentAdmin, db: DbSession
) -> UserRead:
    user = await get_regular_user_by_id(db, user_id)
    if user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    email_changed = payload.email is not None and payload.email != user.email
    if email_changed and await get_user_by_email(db, payload.email) is not None:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Email already registered")
    return await update_user(db, user, payload)


@router.delete("/users/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_admin_user(user_id: int, current_admin: CurrentAdmin, db: DbSession) -> None:
    user = await get_regular_user_by_id(db, user_id)
    if user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    await delete_user(db, user)
