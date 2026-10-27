"""Test fixtures.

Uses an in-memory SQLite database (via aiosqlite) instead of Postgres so the suite runs without
any external services. This means the pgvector-backed `garment_embeddings` table is intentionally
excluded from `create_all` here (SQLite has no vector type) — anything touching the real
embedding column, or real pgvector cosine-distance SQL, needs a real Postgres+pgvector instance
and belongs in a separate, explicitly-marked integration suite (not written yet; Jhuma can smoke
test real semantic search manually via /docs against her real Postgres).

Object storage is likewise faked (FakeStorageService) rather than hitting a real MinIO/S3 —
avatar/garment upload tests care about our own validation/repository logic, not boto3. Garment
vision analysis uses the real MockVisionService (no real provider exists to fake instead), and
Phase 8's embedding generation uses the real MockEmbeddingService the same way -- both bound to
this same db_session so a garment's background processing is visible to the test immediately
after the request that triggered it returns. Embedding *persistence*, however, uses
FakeEmbeddingStore (an in-memory dict, same spirit as FakeStorageService) instead of the real
app/repositories/garment_embedding_repository.py, specifically because that repository writes to
the pgvector column this SQLite database doesn't have -- see the `client` fixture's override of
get_garment_processor, and app/core/deps_processing.py for why that override is necessary at all
(the production version opens its own DB session, which would be invisible to an in-memory
SQLite test database created on a different connection).
"""
from collections.abc import AsyncGenerator
from typing import BinaryIO
from uuid import UUID

import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.database import Base, get_db
from app.core.deps_processing import get_garment_processor
from app.core.deps_storage import storage_dependency
from app.main import app
from app.models.avatar import Avatar
from app.models.garment import Garment
from app.models.garment_image import GarmentImage
from app.models.user import User
from app.models.user_profile import UserProfile
from app.services.embedding.mock import MockEmbeddingService
from app.services.garment_processor import process_garment
from app.services.vision.mock import MockVisionService

TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"


class FakeStorageService:
    def __init__(self) -> None:
        self.uploaded: dict[str, bytes] = {}

    async def upload(self, file: BinaryIO, key: str, content_type: str) -> str:
        self.uploaded[key] = file.read()
        return f"http://fake-storage.test/wardrobe-media/{key}"

    async def delete(self, key: str) -> None:
        self.uploaded.pop(key, None)


class FakeEmbeddingStore:
    """Stands in for app/repositories/garment_embedding_repository.py in tests -- see this
    module's docstring for why the real one can't run against SQLite. Records every upsert
    in-memory so a test can assert on what *would* have been persisted (model/text/vector)
    without needing a real pgvector column."""

    def __init__(self) -> None:
        self.rows: dict[UUID, dict] = {}

    async def upsert(
        self,
        db: AsyncSession,
        *,
        garment_id: UUID,
        embedding: list[float],
        embedding_model: str,
        embedding_text: str,
    ) -> None:
        self.rows[garment_id] = {
            "embedding": embedding,
            "embedding_model": embedding_model,
            "embedding_text": embedding_text,
        }


@pytest_asyncio.fixture
async def db_session() -> AsyncGenerator[AsyncSession, None]:
    engine = create_async_engine(TEST_DATABASE_URL, poolclass=None)
    async with engine.begin() as conn:
        await conn.run_sync(
            lambda sync_conn: Base.metadata.create_all(
                sync_conn,
                tables=[
                    User.__table__,
                    UserProfile.__table__,
                    Avatar.__table__,
                    Garment.__table__,
                    GarmentImage.__table__,
                ],
            )
        )

    session_maker = async_sessionmaker(bind=engine, expire_on_commit=False)
    async with session_maker() as session:
        yield session

    await engine.dispose()


@pytest_asyncio.fixture
async def fake_storage() -> FakeStorageService:
    return FakeStorageService()


@pytest_asyncio.fixture
async def fake_embedding_store() -> FakeEmbeddingStore:
    return FakeEmbeddingStore()


@pytest_asyncio.fixture
async def client(
    db_session: AsyncSession, fake_storage: FakeStorageService, fake_embedding_store: FakeEmbeddingStore
) -> AsyncGenerator[AsyncClient, None]:
    async def override_get_db():
        yield db_session

    def override_get_garment_processor():
        # Bound to this test's own db_session/MockVisionService/MockEmbeddingService/
        # FakeEmbeddingStore rather than the production wrapper's fresh session and real
        # repository, so a garment created in this request is already processed (visible via
        # GET) by the time the triggering request returns -- see module docstring above.
        vision_service = MockVisionService()
        embedding_service = MockEmbeddingService()

        async def _process(garment_id):
            await process_garment(garment_id, db_session, vision_service, embedding_service, fake_embedding_store)

        return _process

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[storage_dependency] = lambda: fake_storage
    app.dependency_overrides[get_garment_processor] = override_get_garment_processor
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac
    app.dependency_overrides.clear()


@pytest_asyncio.fixture
async def auth_headers(client: AsyncClient) -> dict[str, str]:
    """Signs up a fresh user and returns headers ready to use for authenticated requests."""
    response = await client.post(
        "/api/v1/auth/signup",
        json={"email": "fixture-user@example.com", "name": "Fixture", "password": "correct-horse-battery"},
    )
    token = response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}
