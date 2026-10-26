"""Split into its own module (rather than deps.py) for the same reason as deps_storage.py: keeps
provider-specific imports (here, app.services.vision's) out of every module that only needs auth.

get_garment_processor is the seam that lets garment processing run as a FastAPI BackgroundTask
today and move to a Celery/RQ worker later without the route's code changing: the route only
ever sees "a callable that takes a garment_id", never the DB session or vision service directly.
It's also what tests/conftest.py overrides, binding the same app/services/garment_processor.py
logic to the test's own in-memory session instead of a real one.
"""
from collections.abc import Awaitable, Callable
from uuid import UUID

from app.core.database import AsyncSessionLocal
from app.services.garment_processor import process_garment
from app.services.vision import get_vision_service

GarmentProcessor = Callable[[UUID], Awaitable[None]]


async def _process_garment_task(garment_id: UUID) -> None:
    """Production implementation. Runs as a FastAPI BackgroundTask, i.e. after the request that
    scheduled it has already returned its response and closed its own DB session -- so this
    opens a fresh session of its own rather than reusing one from `Depends(get_db)`."""
    async with AsyncSessionLocal() as db:
        await process_garment(garment_id, db, get_vision_service())


def get_garment_processor() -> GarmentProcessor:
    return _process_garment_task
