from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.deps import get_current_user
from app.models.user import User
from app.repositories import garment_embedding_repository, garment_image_repository, garment_repository
from app.schemas.garment import GarmentRead
from app.schemas.wardrobe import (
    WardrobeListResponse,
    WardrobeSearchRequest,
    WardrobeSearchResponse,
    WardrobeSearchResult,
)
from app.services.embedding import get_embedding_service

router = APIRouter(prefix="/wardrobe", tags=["wardrobe"])


@router.get("", response_model=WardrobeListResponse)
async def list_wardrobe(
    category: str | None = Query(default=None),
    subcategory: str | None = Query(default=None),
    color: str | None = Query(default=None),
    style: str | None = Query(default=None),
    processing_status: str | None = Query(default=None),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> WardrobeListResponse:
    """CLAUDE.md sec 6, IMPLEMENTATION_PROMPT.md Phase 9 -- structured filters + pagination.
    Supersedes the earlier minimal `GET /api/v1/garments` list (pulled forward alongside the
    wardrobe UI ahead of this phase; that route has been removed now that this exists)."""
    garments, total = await garment_repository.search_for_user(
        db,
        current_user.id,
        category=category,
        subcategory=subcategory,
        color=color,
        style=style,
        processing_status=processing_status,
        page=page,
        page_size=page_size,
    )
    items = []
    for garment in garments:
        images = await garment_image_repository.list_for_garment(db, garment.id)
        items.append(GarmentRead.from_model(garment, images))
    return WardrobeListResponse(items=items, page=page, page_size=page_size, total=total)


@router.post("/search", response_model=WardrobeSearchResponse)
async def search_wardrobe(
    payload: WardrobeSearchRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> WardrobeSearchResponse:
    """CLAUDE.md sec 6/9, IMPLEMENTATION_PROMPT.md Phase 9 -- semantic search.

    query -> embedding -> pgvector cosine similarity -> user_id filter -> optional category
    filter -> results. User scoping happens inside garment_embedding_repository.semantic_search's
    SQL WHERE clause (CLAUDE.md sec 7: never fetch-then-filter), never in this route.

    Requires a real Postgres+pgvector database -- the embedding/search columns don't exist under
    the SQLite database the unit test suite runs against (see conftest.py's module docstring);
    this route's own tests mock garment_embedding_repository.semantic_search rather than hitting
    real pgvector SQL."""
    embedding_service = get_embedding_service()
    query_vector = await embedding_service.embed(payload.query)

    matches = await garment_embedding_repository.semantic_search(
        db,
        user_id=current_user.id,
        query_vector=query_vector,
        category=payload.category,
        limit=payload.limit,
    )

    if not matches:
        return WardrobeSearchResponse(
            results=[], message="No garments matched your search. Try a different description, or upload more items."
        )

    results = []
    for garment, similarity in matches:
        images = await garment_image_repository.list_for_garment(db, garment.id)
        results.append(
            WardrobeSearchResult(garment=GarmentRead.from_model(garment, images), similarity=similarity)
        )
    return WardrobeSearchResponse(results=results)
