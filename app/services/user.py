from collections.abc import Sequence

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.security import get_password_hash
from app.models.user import User
from app.schemas.admin import AdminUserCreate, AdminUserUpdate


async def get_user_by_email(db: AsyncSession, email: str) -> User | None:
    result = await db.execute(select(User).where(User.email == email))
    return result.scalar_one_or_none()


async def get_regular_user_by_id(db: AsyncSession, user_id: int) -> User | None:
    result = await db.execute(select(User).where(User.id == user_id, User.is_admin.is_(False)))
    return result.scalar_one_or_none()


async def get_regular_users_with_accounts(db: AsyncSession) -> Sequence[User]:
    result = await db.execute(
        select(User).where(User.is_admin.is_(False)).options(selectinload(User.accounts))
    )
    return result.scalars().all()


async def create_user(db: AsyncSession, data: AdminUserCreate) -> User:
    user = User(
        email=data.email,
        full_name=data.full_name,
        hashed_password=get_password_hash(data.password),
        is_admin=False,
    )
    db.add(user)
    await db.flush()
    return user


async def update_user(db: AsyncSession, user: User, data: AdminUserUpdate) -> User:
    updates = data.model_dump(exclude_unset=True)
    password = updates.pop("password", None)
    if password is not None:
        user.hashed_password = get_password_hash(password)
    for field, value in updates.items():
        setattr(user, field, value)
    await db.flush()
    return user


async def delete_user(db: AsyncSession, user: User) -> None:
    await db.delete(user)
    await db.flush()
