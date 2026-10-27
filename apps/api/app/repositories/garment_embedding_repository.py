"""Persistence for garment_embeddings (CLAUDE.md sec 4/8, IMPLEMENTATION_PROMPT.md Phase 8/9).

Uses the real pgvector column (`GarmentEmbedding.embedding`, type `Vector(EMBEDDING_DIMENSION)`)
-- this module can only run against a real Postgres+pgvector database. The unit test suite
(tests/conftest.py) runs against in-memory SQLite, which has no vector column type, so
app/services/garment_processor.py's production wiring (app/core/deps_processing.py) is the only
caller that reaches this module; tests fake the persistence step instead (FakeEmbeddingStore in
conftest.py) rather than exercising this repository, same reasoning as garment_image_repository
vs FakeStorageService for object storage.
"""
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.garment import Garment
from app.models.garment_embedding import GarmentEmbedding


async def upsert(
    db: AsyncSession,
    *,
    garment_id: UUID,
    embedding: list[float],
    embedding_model: str,
    embedding_text: str,
) -> GarmentEmbedding:
    """One embedding row per garment (garment_id is unique on this table) -- re-processing a
    garment (e.g. a future retry endpoint) replaces its previous embedding rather than
    accumulating stale ones."""
    result = await db.execute(select(GarmentEmbedding).where(GarmentEmbedding.garment_id == garment_id))
    row = result.scalar_one_or_none()
    if row is None:
        row = GarmentEmbedding(garment_id=garment_id)
        db.add(row)
    row.embedding = embedding
    row.embedding_model = embedding_model
    row.embedding_text = embedding_text
    await db.flush()
    await db.refresh(row)
    return row


async def semantic_search(
    db: AsyncSession,
    *,
    user_id: UUID,
    query_vector: list[float],
    category: str | None,
    limit: int,
) -> list[tuple[Garment, float]]:
    """pgvector cosine-distance ranking, scoped by user_id at the query level (CLAUDE.md sec 7/9:
    "Never perform vector search across all users. Always scope by user_id.") -- this is a SQL
    JOIN + WHERE, never a fetch-all-then-filter-in-Python.

    Returns (garment, similarity) pairs, nearest first. `similarity` is `1 - cosine_distance`
    (pgvector's `<=>` operator returns cosine *distance*; this repository hands callers the more
    intuitive 0..1-ish similarity instead so the API doesn't leak the raw distance convention)."""
    distance = GarmentEmbedding.embedding.cosine_distance(query_vector)
    stmt = (
        select(Garment, distance.label("distance"))
        .join(GarmentEmbedding, GarmentEmbedding.garment_id == Garment.id)
        .where(Garment.user_id == user_id, Garment.is_active.is_(True))
    )
    if category is not None:
        stmt = stmt.where(Garment.category == category)
    stmt = stmt.order_by(distance.asc()).limit(limit)

    result = await db.execute(stmt)
    return [(garment, 1.0 - float(dist)) for garment, dist in result.all()]
