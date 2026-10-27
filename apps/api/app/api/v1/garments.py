import io
import uuid

from fastapi import APIRouter, BackgroundTasks, Depends, File, Form, HTTPException, Response, UploadFile, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.deps import get_current_user
from app.core.deps_processing import GarmentProcessor, get_garment_processor
from app.core.deps_storage import storage_dependency
from app.core.image_validation import ALLOWED_IMAGE_CONTENT_TYPES, MAX_IMAGE_SIZE_BYTES, extension_for_content_type
from app.models.user import User
from app.repositories import garment_image_repository, garment_repository
from app.schemas.garment import GarmentRead, GarmentUpdate
from app.services.storage import StorageService

router = APIRouter(prefix="/garments", tags=["garments"])


@router.post("", response_model=GarmentRead, status_code=status.HTTP_201_CREATED)
async def upload_garment(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    name: str | None = Form(default=None),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    storage: StorageService = Depends(storage_dependency),
    processor: GarmentProcessor = Depends(get_garment_processor),
) -> GarmentRead:
    """validate file -> create garment(pending) -> upload image -> create garment_image ->
    enqueue AI analysis -> return garment (CLAUDE.md sec 8). The response reflects the
    pre-analysis state (processing_status="pending") since analysis runs in the background after
    this returns, per IMPLEMENTATION_PROMPT.md Phase 6: "should not block unnecessarily on a slow
    AI provider"."""
    if file.content_type not in ALLOWED_IMAGE_CONTENT_TYPES:
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail=f"Unsupported image type '{file.content_type}'. Allowed: "
            f"{', '.join(sorted(ALLOWED_IMAGE_CONTENT_TYPES))}",
        )

    contents = await file.read()
    if len(contents) == 0:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Empty file")
    if len(contents) > MAX_IMAGE_SIZE_BYTES:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"Image exceeds the {MAX_IMAGE_SIZE_BYTES // (1024 * 1024)}MB limit",
        )

    garment = await garment_repository.create_pending(db, user_id=current_user.id, name=name)

    extension = extension_for_content_type(file.content_type)
    key = f"garments/{current_user.id}/{garment.id}/{uuid.uuid4()}.{extension}"
    image_url = await storage.upload(io.BytesIO(contents), key, file.content_type)
    await garment_image_repository.create(db, garment_id=garment.id, image_url=image_url)

    await db.commit()

    # Scheduled to run after this response is sent -- see app/core/deps_processing.py for why
    # the processor opens its own DB session rather than reusing this request's.
    background_tasks.add_task(processor, garment.id)

    images = await garment_image_repository.list_for_garment(db, garment.id)
    return GarmentRead.from_model(garment, images)


@router.get("/{garment_id}", response_model=GarmentRead)
async def get_garment(
    garment_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> GarmentRead:
    garment = await garment_repository.get_by_id_for_user(db, garment_id, current_user.id)
    if garment is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Garment not found")
    images = await garment_image_repository.list_for_garment(db, garment_id)
    return GarmentRead.from_model(garment, images)


@router.put("/{garment_id}", response_model=GarmentRead)
async def update_garment(
    garment_id: uuid.UUID,
    payload: GarmentUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> GarmentRead:
    garment = await garment_repository.get_by_id_for_user(db, garment_id, current_user.id)
    if garment is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Garment not found")
    garment = await garment_repository.update_fields(db, garment, payload)
    await db.commit()
    images = await garment_image_repository.list_for_garment(db, garment_id)
    return GarmentRead.from_model(garment, images)


@router.delete("/{garment_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_garment(
    garment_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> Response:
    """Soft delete (is_active=False) rather than a row delete -- preserves outfit_items FK
    integrity for any outfit that already references this garment (CLAUDE.md sec 4).

    Returns an explicit `Response(status_code=204)` rather than `None` -- FastAPI's default
    handling for a bare `None` return still serializes it as a JSON body (literal `null`, 4
    bytes) with a Content-Length header, even when the route's status_code is 204. A 204
    response must have NO body at all per the HTTP spec, so that default behavior produces a
    technically malformed response: real browsers can reject or mishandle it, while it slips
    past tests that talk ASGI directly (no real wire-protocol parsing). Returning a real, empty
    `Response` bypasses FastAPI's default serialization entirely and sends a genuinely empty
    body. (Found when Jhuma's real browser couldn't delete a garment -- see BUILD_STATUS.md.)
    """
    garment = await garment_repository.get_by_id_for_user(db, garment_id, current_user.id)
    if garment is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Garment not found")
    await garment_repository.soft_delete(db, garment)
    await db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)
