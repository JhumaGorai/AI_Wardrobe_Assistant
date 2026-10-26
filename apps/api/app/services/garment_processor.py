"""Pure garment-processing logic (CLAUDE.md sec 8's pipeline from "background job" through
"status=completed"/"failed"), deliberately decoupled from:

  - HOW it's invoked -- FastAPI BackgroundTasks today, a Celery/RQ worker later, with no change
    to this function's signature (IMPLEMENTATION_PROMPT.md Phase 6's explicit requirement).
  - WHICH db session / vision service it's given -- app/core/deps_processing.py supplies real
    ones in production; tests/conftest.py overrides that dependency with a closure bound to the
    test's own in-memory session, so this same code path is exercised by the test suite too.
"""
from uuid import UUID

from pydantic import ValidationError
from sqlalchemy.ext.asyncio import AsyncSession

from app.repositories import garment_image_repository, garment_repository
from app.services.vision.base import VisionService

# Never surface the real exception text to the user -- it could contain provider-internal
# details (CLAUDE.md sec 7: "never expose ... internal errors"). Retry is still possible: this
# leaves the garment row and its uploaded image intact, just with processing_status="failed".
_SAFE_ERROR_MESSAGE = "Garment image analysis failed. You can retry by re-uploading the image."


async def process_garment(garment_id: UUID, db: AsyncSession, vision_service: VisionService) -> None:
    garment = await garment_repository.get_by_id(db, garment_id)
    if garment is None:
        # Deleted (or never existed) before processing ran -- nothing to do.
        return

    images = await garment_image_repository.list_for_garment(db, garment_id)
    if not images:
        await garment_repository.mark_failed(db, garment, _SAFE_ERROR_MESSAGE)
        await db.commit()
        return

    try:
        analysis = await vision_service.analyze_garment(images[0].image_url)
    except ValidationError:
        # Provider returned data that doesn't match GarmentAnalysis's shape -- never let that
        # corrupt the garment row.
        await garment_repository.mark_failed(db, garment, _SAFE_ERROR_MESSAGE)
        await db.commit()
        return
    except Exception:
        # Any other provider error (network, timeout, 5xx, ...) -- same safe handling.
        await garment_repository.mark_failed(db, garment, _SAFE_ERROR_MESSAGE)
        await db.commit()
        return

    await garment_repository.apply_analysis(db, garment, analysis)
    await db.commit()
