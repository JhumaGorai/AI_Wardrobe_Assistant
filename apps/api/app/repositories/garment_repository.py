from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.garment import Garment
from app.schemas.garment import GarmentAnalysis, GarmentUpdate


async def search_for_user(
    db: AsyncSession,
    user_id: UUID,
    *,
    category: str | None = None,
    subcategory: str | None = None,
    color: str | None = None,
    style: str | None = None,
    processing_status: str | None = None,
    page: int = 1,
    page_size: int = 20,
) -> tuple[list[Garment], int]:
    """Backs `GET /api/v1/wardrobe` (CLAUDE.md sec 6, IMPLEMENTATION_PROMPT.md Phase 9) --
    supersedes the minimal `list_for_user`/`GET /api/v1/garments` list that was pulled forward
    ahead of this phase alongside the wardrobe UI (that stopgap route has been removed now that
    this exists). Always scoped by user_id and excludes soft-deleted rows, same as every other
    garment query in this module (CLAUDE.md sec 7).

    `category`/`subcategory`/`processing_status` are plain columns, so they're pushed down into
    the SQL WHERE clause. `color`/`style` live *inside* a JSON array column (`colors`/
    `style_tags`); JSON-array "contains" filtering isn't portable across SQLite (used by the test
    suite) and Postgres (production) at the SQL level, so -- deliberately keeping this simple
    rather than reaching for a premature cross-dialect abstraction (CLAUDE.md sec 17 principle
    5) -- those two are applied in Python after the SQL-filtered rows come back. Fine at the
    scale of one user's own wardrobe; worth revisiting with a real SQL filter if wardrobes grow
    very large."""
    conditions = [Garment.user_id == user_id, Garment.is_active.is_(True)]
    if category is not None:
        conditions.append(Garment.category == category)
    if subcategory is not None:
        conditions.append(Garment.subcategory == subcategory)
    if processing_status is not None:
        conditions.append(Garment.processing_status == processing_status)

    result = await db.execute(select(Garment).where(*conditions).order_by(Garment.created_at.desc()))
    garments = list(result.scalars().all())

    if color is not None:
        garments = [g for g in garments if color in (g.colors or [])]
    if style is not None:
        garments = [g for g in garments if style in (g.style_tags or [])]

    total = len(garments)
    start = (page - 1) * page_size
    page_items = garments[start : start + page_size]
    return page_items, total


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
    """Fills in the AI-provided attribute fields only -- does NOT mark the garment completed.
    CLAUDE.md sec 8's pipeline runs embedding generation *after* this step and *before*
    status=completed ("update garment attributes -> construct embedding text -> generate
    embedding -> store vector -> status=completed"), so the garment stays in its prior status
    (still "pending") until app/services/garment_processor.py calls mark_completed() once the
    embedding has actually been stored -- see that module for why."""
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
    await db.flush()
    await db.refresh(garment)
    return garment


async def mark_completed(db: AsyncSession, garment: Garment) -> Garment:
    """The last step of CLAUDE.md sec 8's pipeline -- only called once vision analysis AND
    embedding generation/storage have both succeeded."""
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
