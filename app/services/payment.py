from collections.abc import Sequence

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.payment import Payment


async def get_payments_by_user_id(db: AsyncSession, user_id: int) -> Sequence[Payment]:
    result = await db.execute(
        select(Payment).where(Payment.user_id == user_id).order_by(Payment.created_at.desc())
    )
    return result.scalars().all()
