"""Data access for the `users` table.

Kept thin on purpose for the MVP; the point of a repository layer here is to give business logic
a single place to change if the persistence details evolve, not to add ceremony.
"""
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User


async def get_by_email(db: AsyncSession, email: str) -> User | None:
    result = await db.execute(select(User).where(User.email == email))
    return result.scalar_one_or_none()


async def get_by_id(db: AsyncSession, user_id) -> User | None:
    result = await db.execute(select(User).where(User.id == user_id))
    return result.scalar_one_or_none()


async def create(db: AsyncSession, *, email: str, name: str | None, password_hash: str) -> User:
    user = User(email=email, name=name, password_hash=password_hash)
    db.add(user)
    await db.flush()
    await db.refresh(user)
    return user
