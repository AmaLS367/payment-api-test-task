from fastapi import APIRouter

from app.api.deps import CurrentUser, DbSession
from app.api.openapi import UNAUTHORIZED_RESPONSE
from app.schemas.account import AccountRead
from app.schemas.payment import PaymentRead
from app.schemas.user import UserRead
from app.services.account import get_accounts_by_user_id
from app.services.payment import get_payments_by_user_id

router = APIRouter(prefix="/users", tags=["Users"])


@router.get(
    "/me",
    response_model=UserRead,
    summary="Get the current user",
    description="Returns the profile associated with the supplied Bearer token.",
    responses={401: UNAUTHORIZED_RESPONSE},
)
async def read_current_user(current_user: CurrentUser) -> UserRead:
    return UserRead.model_validate(current_user)


@router.get(
    "/me/accounts",
    response_model=list[AccountRead],
    summary="List the current user's accounts",
    description="Returns all accounts owned by the authenticated user.",
    responses={401: UNAUTHORIZED_RESPONSE},
)
async def read_current_user_accounts(
    current_user: CurrentUser, db: DbSession
) -> list[AccountRead]:
    accounts = await get_accounts_by_user_id(db, current_user.id)
    return [AccountRead.model_validate(acc) for acc in accounts]


@router.get(
    "/me/payments",
    response_model=list[PaymentRead],
    summary="List the current user's payments",
    description="Returns payment records belonging to the authenticated user.",
    responses={401: UNAUTHORIZED_RESPONSE},
)
async def read_current_user_payments(
    current_user: CurrentUser, db: DbSession
) -> list[PaymentRead]:
    payments = await get_payments_by_user_id(db, current_user.id)
    return [PaymentRead.model_validate(p) for p in payments]

