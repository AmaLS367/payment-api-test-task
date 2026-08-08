from collections.abc import Sequence

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.account import Account


async def get_accounts_by_user_id(db: AsyncSession, user_id: int) -> Sequence[Account]:
    result = await db.execute(select(Account).where(Account.user_id == user_id))
    return result.scalars().all()
