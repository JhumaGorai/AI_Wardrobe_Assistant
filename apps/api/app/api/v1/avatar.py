import io
import uuid

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.deps import get_current_user
from app.core.deps_storage import storage_dependency
from app.models.user import User
from app.repositories import avatar_repository
from app.schemas.avatar import ALLOWED_AVATAR_CONTENT_TYPES, MAX_AVATAR_SIZE_BYTES, AvatarRead
from app.services.storage import StorageService

router = APIRouter(prefix="/avatar", tags=["avatar"])

_EXTENSION_BY_CONTENT_TYPE = {
    "image/jpeg": "jpg",
    "image/png": "png",
    "image/webp": "webp",
}


@router.get("", response_model=list[AvatarRead])
async def list_avatars(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[AvatarRead]:
    avatars = await avatar_repository.list_for_user(db, current_user.id)
    return [AvatarRead.model_validate(a) for a in avatars]


@router.post("", response_model=AvatarRead, status_code=status.HTTP_201_CREATED)
async def upload_avatar(
    file: UploadFile = File(...),
    type: str = Form(default="full_body"),
    is_primary: bool = Form(default=False),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    storage: StorageService = Depends(storage_dependency),
) -> AvatarRead:
    if file.content_type not in ALLOWED_AVATAR_CONTENT_TYPES:
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail=f"Unsupported image type '{file.content_type}'. Allowed: "
            f"{', '.join(sorted(ALLOWED_AVATAR_CONTENT_TYPES))}",
        )

    contents = await file.read()
    if len(contents) > MAX_AVATAR_SIZE_BYTES:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"Image exceeds the {MAX_AVATAR_SIZE_BYTES // (1024 * 1024)}MB limit",
        )
    if len(contents) == 0:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Empty file")

    extension = _EXTENSION_BY_CONTENT_TYPE[file.content_type]
    key = f"avatars/{current_user.id}/{uuid.uuid4()}.{extension}"

    image_url = await storage.upload(io.BytesIO(contents), key, file.content_type)

    avatar = await avatar_repository.create(
        db,
        user_id=current_user.id,
        image_url=image_url,
        avatar_type=type,
        is_primary=is_primary,
    )
    await db.commit()
    return AvatarRead.model_validate(avatar)
