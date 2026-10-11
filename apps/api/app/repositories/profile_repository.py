from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user_profile import UserProfile
from app.schemas.profile import UserProfileUpdate


async def get_by_user_id(db: AsyncSession, user_id: UUID) -> UserProfile | None:
    result = await db.execute(select(UserProfile).where(UserProfile.user_id == user_id))
    return result.scalar_one_or_none()


async def upsert(db: AsyncSession, user_id: UUID, payload: UserProfileUpdate) -> UserProfile:
    """Creates the profile on first write, updates it on every subsequent one. There is no
    separate "create profile" endpoint in the API contract (CLAUDE.md sec 6 only lists
    GET/PUT /api/v1/profile), so PUT does double duty."""
    profile = await get_by_user_id(db, user_id)
    data = payload.model_dump()

    if profile is None:
        profile = UserProfile(user_id=user_id, **data)
        db.add(profile)
    else:
        for field, value in data.items():
            setattr(profile, field, value)

    await db.flush()
    await db.refresh(profile)
    return profile
