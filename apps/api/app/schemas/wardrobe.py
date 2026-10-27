from pydantic import BaseModel, Field

from app.schemas.garment import GarmentRead


class WardrobeListResponse(BaseModel):
    """`GET /api/v1/wardrobe` (CLAUDE.md sec 6, IMPLEMENTATION_PROMPT.md Phase 9)."""

    items: list[GarmentRead]
    page: int
    page_size: int
    total: int


class WardrobeSearchRequest(BaseModel):
    """`POST /api/v1/wardrobe/search` body -- matches the example in CLAUDE.md sec 6 /
    IMPLEMENTATION_PROMPT.md Phase 9:
        {"query": "minimal sophisticated dinner top", "category": "top", "limit": 10}
    """

    query: str = Field(min_length=1)
    category: str | None = None
    limit: int = Field(default=10, ge=1, le=50)


class WardrobeSearchResult(BaseModel):
    """A garment plus how well it matched the query. `similarity` is `1 - cosine_distance`
    (higher = closer), not a calibrated probability -- useful for relative ranking/display, not
    for an absolute "this is a 94% match" claim."""

    garment: GarmentRead
    similarity: float


class WardrobeSearchResponse(BaseModel):
    results: list[WardrobeSearchResult]
    message: str | None = None
