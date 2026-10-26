from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.garment import Garment
from app.schemas.garment import GarmentAnalysis, GarmentUpdate


async def list_for_user(db: AsyncSession, user_id: UUID) -> list[Garment]:
    """Minimal, unfiltered listing (newest first), excluding soft-deleted rows. The full
    `GET /api/v1/wardrobe` (search/filter/pagination -- CLAUDE.md sec 6, IMPLEMENTATION_PROMPT.md
    Phase 9) isn't built yet; this is added ahead of it, pulled forward alongside the wardrobe UI,
    because that UI needs *some* way to show "garments you own" today. Phase 9 can supersede or
    extend this later without changing this CRUD module's contract."""
    result = await db.execute(
        select(Garment)
        .where(Garment.user_id == user_id, Garment.is_active.is_(True))
        .order_by(Garment.created_at.desc())
    )
    return list(result.scalars().all())


async def get_by_id_for_user(db: AsyncSession, garment_id: UUID, user_id: UUID) -> Garment | None:
    """The only lookup user-facing routes should use -- scopes by user_id at the query level
    (CLAUDE.md sec 7), never by fetching-then-filtering in Python. Excludes soft-deleted rows so
    a deleted garment behaves as not-found to its owner too."""
    result = await db.execute(
        select(Garment).where(
            Garment.id == garment_id,
            Garment.user_id == user_id,
            Garment.is_active.is_(True),
        )
    )
    return result.scalar_one_or_none()


async def get_by_id(db: AsyncSession, garment_id: UUID) -> Garment | None:
    """Unscoped by user_id -- for internal background processing ONLY (see
    app/services/garment_processor.py). Never call this from a user-facing route; the garment_id
    it receives was already authorized when the garment was created, not supplied fresh by a
    client request."""
    result = await db.execute(select(Garment).where(Garment.id == garment_id))
    return result.scalar_one_or_none()


async def create_pending(db: AsyncSession, *, user_id: UUID, name: str | None) -> Garment:
    garment = Garment(user_id=user_id, name=name, processing_status="pending")
    db.add(garment)
    await db.flush()
    await db.refresh(garment)
    return garment


async def apply_analysis(db: AsyncSession, garment: Garment, analysis: GarmentAnalysis) -> Garment:
    garment.category = analysis.category
    garment.subcategory = analysis.subcategory
    garment.colors = analysis.colors
    garment.pattern = analysis.pattern
    garment.material = analysis.material
    garment.fit = analysis.fit
    garment.formality = analysis.formality
    garment.seasons = analysis.seasons
    garment.style_tags = analysis.style_tags
    garment.description = analysis.description
    garment.processing_status = "completed"
    garment.processing_error = None
    await db.flush()
    await db.refresh(garment)
    return garment


async def mark_failed(db: AsyncSession, garment: Garment, error_message: str) -> Garment:
    garment.processing_status = "failed"
    garment.processing_error = error_message
    await db.flush()
    await db.refresh(garment)
    return garment


async def update_fields(db: AsyncSession, garment: Garment, payload: GarmentUpdate) -> Garment:
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(garment, field, value)
    await db.flush()
    await db.refresh(garment)
    return garment


async def soft_delete(db: AsyncSession, garment: Garment) -> None:
    garment.is_active = False
    await db.flush()
