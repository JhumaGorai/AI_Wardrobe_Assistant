from uuid import UUID

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.avatar import Avatar


async def list_for_user(db: AsyncSession, user_id: UUID) -> list[Avatar]:
    result = await db.execute(
        select(Avatar).where(Avatar.user_id == user_id).order_by(Avatar.created_at.desc())
    )
    return list(result.scalars().all())


async def get_by_id_for_user(db: AsyncSession, avatar_id: UUID, user_id: UUID) -> Avatar | None:
    result = await db.execute(
        select(Avatar).where(Avatar.id == avatar_id, Avatar.user_id == user_id)
    )
    return result.scalar_one_or_none()


async def create(
    db: AsyncSession,
    *,
    user_id: UUID,
    image_url: str,
    avatar_type: str,
    is_primary: bool,
) -> Avatar:
    if is_primary:
        # Only one primary avatar per user — unset any existing one first.
        await db.execute(
            update(Avatar).where(Avatar.user_id == user_id, Avatar.is_primary.is_(True)).values(is_primary=False)
        )

    avatar = Avatar(user_id=user_id, image_url=image_url, type=avatar_type, is_primary=is_primary)
    db.add(avatar)
    await db.flush()
    await db.refresh(avatar)
    return avatar
