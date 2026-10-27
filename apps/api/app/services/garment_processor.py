"""Pure garment-processing logic (CLAUDE.md sec 8's full pipeline, "background job" through
"status=completed"/"failed", now including Phase 8's embedding step), deliberately decoupled
from:

  - HOW it's invoked -- FastAPI BackgroundTasks today, a Celery/RQ worker later, with no change
    to this function's signature (IMPLEMENTATION_PROMPT.md Phase 6's explicit requirement).
  - WHICH db session / vision service / embedding service / embedding store it's given --
    app/core/deps_processing.py supplies real ones in production; tests/conftest.py overrides
    that dependency with a closure bound to the test's own in-memory session, a MockVisionService,
    a MockEmbeddingService, and a FakeEmbeddingStore (the real embedding_store writes to the
    pgvector `garment_embeddings` table, which the SQLite test database can't represent -- see
    conftest.py's module docstring), so this same code path is exercised by the test suite too.
"""
from typing import Protocol
from uuid import UUID

from pydantic import ValidationError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.repositories import garment_image_repository, garment_repository
from app.services.embedding.base import EmbeddingService
from app.services.embedding_text import build_embedding_text
from app.services.vision.base import VisionService

# Never surface the real exception text to the user -- it could contain provider-internal
# details (CLAUDE.md sec 7: "never expose ... internal errors"). Retry is still possible: this
# leaves the garment row and its uploaded image intact, just with processing_status="failed".
_SAFE_ERROR_MESSAGE = "Garment image analysis failed. You can retry by re-uploading the image."


class EmbeddingStore(Protocol):
    """The seam that keeps this module's embedding-persistence step swappable -- the production
    implementation is app/repositories/garment_embedding_repository.py (a real pgvector write);
    tests substitute an in-memory fake. Matches the shape of that repository's `upsert`."""

    async def upsert(
        self,
        db: AsyncSession,
        *,
        garment_id: UUID,
        embedding: list[float],
        embedding_model: str,
        embedding_text: str,
    ) -> None:
        ...


async def process_garment(
    garment_id: UUID,
    db: AsyncSession,
    vision_service: VisionService,
    embedding_service: EmbeddingService,
    embedding_store: EmbeddingStore,
) -> None:
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

    garment = await garment_repository.apply_analysis(db, garment, analysis)

    # Phase 8: construct embedding text -> generate embedding -> store vector -> status=completed
    # (CLAUDE.md sec 8). Any failure here gets the exact same safe-error treatment as a vision
    # failure above -- the garment keeps its AI-filled attributes (useful on its own even without
    # a working embedding) but is marked "failed" rather than "completed", since it won't be
    # findable via semantic search (Phase 9) until a retry succeeds.
    embedding_text = build_embedding_text(garment)
    try:
        vector = await embedding_service.embed(embedding_text)
    except Exception:
        await garment_repository.mark_failed(db, garment, _SAFE_ERROR_MESSAGE)
        await db.commit()
        return

    expected_dimension = get_settings().embedding_dimension
    if len(vector) != expected_dimension:
        # "Do not silently truncate or pad vectors" (IMPLEMENTATION_PROMPT.md Phase 8) -- a
        # provider/model misconfiguration that returned the wrong width is a safe-error case,
        # never a reason to reshape the vector or write a mismatched column width.
        await garment_repository.mark_failed(db, garment, _SAFE_ERROR_MESSAGE)
        await db.commit()
        return

    await embedding_store.upsert(
        db,
        garment_id=garment.id,
        embedding=vector,
        embedding_model=embedding_service.model_name,
        embedding_text=embedding_text,
    )
    await garment_repository.mark_completed(db, garment)
    await db.commit()
