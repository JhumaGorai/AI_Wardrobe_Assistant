"""Split into its own module (rather than deps.py) for the same reason as deps_storage.py: keeps
provider-specific imports (here, app.services.vision's and app.services.embedding's) out of every
module that only needs auth.

get_garment_processor is the seam that lets garment processing run as a FastAPI BackgroundTask
today and move to a Celery/RQ worker later without the route's code changing: the route only
ever sees "a callable that takes a garment_id", never the DB session, vision service, embedding
service, or embedding store directly. It's also what tests/conftest.py overrides, binding the
same app/services/garment_processor.py logic to the test's own in-memory session, a
MockVisionService, a MockEmbeddingService, and a FakeEmbeddingStore instead of a real one.
"""
from collections.abc import Awaitable, Callable
from uuid import UUID

from app.core.database import AsyncSessionLocal
from app.repositories import garment_embedding_repository
from app.services.embedding import get_embedding_service
from app.services.garment_processor import process_garment
from app.services.vision import get_vision_service

GarmentProcessor = Callable[[UUID], Awaitable[None]]


async def _process_garment_task(garment_id: UUID) -> None:
    """Production implementation. Runs as a FastAPI BackgroundTask, i.e. after the request that
    scheduled it has already returned its response and closed its own DB session -- so this
    opens a fresh session of its own rather than reusing one from `Depends(get_db)`.

    `garment_embedding_repository` (the module itself) is passed as the embedding store -- its
    `upsert` function matches the shape process_garment.EmbeddingStore expects, so no wrapper
    class is needed for the real implementation; only tests need a distinct fake."""
    async with AsyncSessionLocal() as db:
        await process_garment(garment_id, db, get_vision_service(), get_embedding_service(), garment_embedding_repository)


def get_garment_processor() -> GarmentProcessor:
    return _process_garment_task
