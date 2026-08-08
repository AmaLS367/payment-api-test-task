from fastapi import APIRouter

from app.api.deps import CurrentUser, DbSession
from app.schemas.account import AccountRead
from app.schemas.payment import PaymentRead
from app.schemas.user import UserRead
from app.services.account import get_accounts_by_user_id
from app.services.payment import get_payments_by_user_id

router = APIRouter(prefix="/users", tags=["users"])


@router.get("/me", response_model=UserRead)
async def read_current_user(current_user: CurrentUser) -> UserRead:
    return current_user


@router.get("/me/accounts", response_model=list[AccountRead])
async def read_current_user_accounts(
    current_user: CurrentUser, db: DbSession
) -> list[AccountRead]:
    return await get_accounts_by_user_id(db, current_user.id)


@router.get("/me/payments", response_model=list[PaymentRead])
async def read_current_user_payments(
    current_user: CurrentUser, db: DbSession
) -> list[PaymentRead]:
    return await get_payments_by_user_id(db, current_user.id)
