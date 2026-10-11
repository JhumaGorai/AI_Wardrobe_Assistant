"""Test fixtures.

Uses an in-memory SQLite database (via aiosqlite) instead of Postgres so the suite runs without
any external services. This means the pgvector-backed `garment_embeddings` table is intentionally
excluded from `create_all` here (SQLite has no vector type) — anything touching embeddings needs a
real Postgres+pgvector instance and belongs in a separate, explicitly-marked integration suite.

Object storage is likewise faked (FakeStorageService) rather than hitting a real MinIO/S3 —
avatar upload tests care about our own validation/repository logic, not boto3.
"""
from collections.abc import AsyncGenerator
from typing import BinaryIO

import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.database import Base, get_db
from app.core.deps_storage import storage_dependency
from app.main import app
from app.models.avatar import Avatar
from app.models.user import User
from app.models.user_profile import UserProfile

TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"


class FakeStorageService:
    def __init__(self) -> None:
        self.uploaded: dict[str, bytes] = {}

    async def upload(self, file: BinaryIO, key: str, content_type: str) -> str:
        self.uploaded[key] = file.read()
        return f"http://fake-storage.test/wardrobe-media/{key}"

    async def delete(self, key: str) -> None:
        self.uploaded.pop(key, None)


@pytest_asyncio.fixture
async def db_session() -> AsyncGenerator[AsyncSession, None]:
    engine = create_async_engine(TEST_DATABASE_URL, poolclass=None)
    async with engine.begin() as conn:
        await conn.run_sync(
            lambda sync_conn: Base.metadata.create_all(
                sync_conn, tables=[User.__table__, UserProfile.__table__, Avatar.__table__]
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
async def client(db_session: AsyncSession, fake_storage: FakeStorageService) -> AsyncGenerator[AsyncClient, None]:
    async def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[storage_dependency] = lambda: fake_storage
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
