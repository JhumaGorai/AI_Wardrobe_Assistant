from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.deps import get_current_user
from app.models.user import User
from app.repositories import profile_repository
from app.schemas.profile import UserProfileRead, UserProfileUpdate

router = APIRouter(prefix="/profile", tags=["profile"])


@router.get("", response_model=UserProfileRead)
async def get_profile(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> UserProfileRead:
    profile = await profile_repository.get_by_user_id(db, current_user.id)
    if profile is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Profile not created yet — PUT /api/v1/profile to create one",
        )
    return UserProfileRead.model_validate(profile)


@router.put("", response_model=UserProfileRead)
async def update_profile(
    payload: UserProfileUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> UserProfileRead:
    profile = await profile_repository.upsert(db, current_user.id, payload)
    await db.commit()
    return UserProfileRead.model_validate(profile)
