"""API tests for Phase 9 (CLAUDE.md sec 6/14, IMPLEMENTATION_PROMPT.md Phase 9).

GET /api/v1/wardrobe runs against the real SQLite test database -- its filters/pagination are
plain-column SQL plus a small in-Python pass for the JSON-array color/style filters (see
garment_repository.search_for_user), none of which touch pgvector. POST /api/v1/wardrobe/search
monkeypatches garment_embedding_repository.semantic_search instead of calling it for real: real
pgvector cosine-distance SQL can't run against SQLite (see conftest.py's module docstring), so
these tests verify the ROUTE's own contract -- auth, request validation, user_id scoping,
category/limit passthrough, response shape -- and leave verifying the actual ranking SQL to a
real Postgres (Jhuma can smoke test this manually via /docs)."""
from uuid import UUID

import pytest
from httpx import AsyncClient

from app.repositories import garment_embedding_repository, garment_repository

pytestmark = pytest.mark.asyncio


def _image_file(name: str = "shirt.jpg", content: bytes = b"fake-image-bytes", content_type: str = "image/jpeg"):
    return {"file": (name, content, content_type)}


# --- GET /api/v1/wardrobe -----------------------------------------------------------------


async def test_list_wardrobe_requires_auth(client: AsyncClient):
    response = await client.get("/api/v1/wardrobe")
    assert response.status_code == 401


async def test_list_wardrobe_scopes_by_user_and_excludes_deleted(
    client: AsyncClient, auth_headers: dict[str, str]
):
    first = await client.post(
        "/api/v1/garments", files=_image_file(), data={"name": "First"}, headers=auth_headers
    )
    await client.post("/api/v1/garments", files=_image_file(), data={"name": "Second"}, headers=auth_headers)
    first_id = first.json()["id"]
    # Soft-deleted garments must not appear.
    await client.delete(f"/api/v1/garments/{first_id}", headers=auth_headers)

    other_signup = await client.post(
        "/api/v1/auth/signup",
        json={"email": "wardrobe-other@example.com", "name": "Other", "password": "another-password"},
    )
    other_headers = {"Authorization": f"Bearer {other_signup.json()['access_token']}"}
    await client.post("/api/v1/garments", files=_image_file(), data={"name": "Not mine"}, headers=other_headers)

    response = await client.get("/api/v1/wardrobe", headers=auth_headers)
    assert response.status_code == 200
    body = response.json()
    assert [item["name"] for item in body["items"]] == ["Second"]
    assert body["total"] == 1


async def test_list_wardrobe_filters_by_category(client: AsyncClient, auth_headers: dict[str, str]):
    upload = await client.post("/api/v1/garments", files=_image_file(), headers=auth_headers)
    garment_id = upload.json()["id"]
    # Pin the category explicitly rather than relying on the mock vision service's (seeded but
    # unpredictable-to-the-test) choice, so this assertion is deterministic.
    await client.put(f"/api/v1/garments/{garment_id}", json={"category": "footwear"}, headers=auth_headers)

    matching = await client.get("/api/v1/wardrobe", params={"category": "footwear"}, headers=auth_headers)
    assert [item["id"] for item in matching.json()["items"]] == [garment_id]

    non_matching = await client.get("/api/v1/wardrobe", params={"category": "dress"}, headers=auth_headers)
    assert non_matching.json()["items"] == []


async def test_list_wardrobe_filters_by_color_and_style(client: AsyncClient, auth_headers: dict[str, str]):
    upload = await client.post("/api/v1/garments", files=_image_file(), headers=auth_headers)
    garment_id = upload.json()["id"]
    await client.put(
        f"/api/v1/garments/{garment_id}",
        json={"colors": ["cobalt"], "style_tags": ["avant-garde"]},
        headers=auth_headers,
    )

    by_color = await client.get("/api/v1/wardrobe", params={"color": "cobalt"}, headers=auth_headers)
    assert [item["id"] for item in by_color.json()["items"]] == [garment_id]

    by_missing_color = await client.get("/api/v1/wardrobe", params={"color": "magenta"}, headers=auth_headers)
    assert by_missing_color.json()["items"] == []

    by_style = await client.get("/api/v1/wardrobe", params={"style": "avant-garde"}, headers=auth_headers)
    assert [item["id"] for item in by_style.json()["items"]] == [garment_id]


async def test_list_wardrobe_pagination(client: AsyncClient, auth_headers: dict[str, str]):
    for i in range(3):
        await client.post(
            "/api/v1/garments", files=_image_file(), data={"name": f"Item {i}"}, headers=auth_headers
        )

    page_1 = await client.get("/api/v1/wardrobe", params={"page": 1, "page_size": 2}, headers=auth_headers)
    page_2 = await client.get("/api/v1/wardrobe", params={"page": 2, "page_size": 2}, headers=auth_headers)

    assert page_1.json()["total"] == 3
    assert len(page_1.json()["items"]) == 2
    assert len(page_2.json()["items"]) == 1
    page_1_ids = {item["id"] for item in page_1.json()["items"]}
    page_2_ids = {item["id"] for item in page_2.json()["items"]}
    assert page_1_ids.isdisjoint(page_2_ids)


# --- POST /api/v1/wardrobe/search -----------------------------------------------------------


async def test_search_wardrobe_requires_auth(client: AsyncClient):
    response = await client.post("/api/v1/wardrobe/search", json={"query": "blue top"})
    assert response.status_code == 401


async def test_search_wardrobe_rejects_empty_query(client: AsyncClient, auth_headers: dict[str, str]):
    response = await client.post("/api/v1/wardrobe/search", json={"query": ""}, headers=auth_headers)
    assert response.status_code == 422


async def test_search_wardrobe_scopes_by_current_user_and_passes_filters(
    client: AsyncClient, auth_headers: dict[str, str], monkeypatch
):
    upload = await client.post("/api/v1/garments", files=_image_file(), headers=auth_headers)
    expected_user_id = upload.json()["user_id"]

    calls = []

    async def fake_semantic_search(db, *, user_id, query_vector, category, limit):
        calls.append({"user_id": str(user_id), "category": category, "limit": limit})
        return []

    monkeypatch.setattr(garment_embedding_repository, "semantic_search", fake_semantic_search)

    response = await client.post(
        "/api/v1/wardrobe/search",
        json={"query": "minimal sophisticated dinner top", "category": "top", "limit": 5},
        headers=auth_headers,
    )
    assert response.status_code == 200
    body = response.json()
    assert body["results"] == []
    assert body["message"]  # a helpful message, not just an empty list, when nothing matches

    assert len(calls) == 1
    # The user_id reaching the repository must be the authenticated user's own -- never
    # client-supplied -- per CLAUDE.md sec 7/9: "Never perform vector search across all users."
    assert calls[0]["user_id"] == expected_user_id
    assert calls[0]["category"] == "top"
    assert calls[0]["limit"] == 5


async def test_search_wardrobe_returns_similarity_scored_results(
    client: AsyncClient, auth_headers: dict[str, str], db_session, monkeypatch
):
    upload = await client.post("/api/v1/garments", files=_image_file(), headers=auth_headers)
    garment_id = upload.json()["id"]
    garment = await garment_repository.get_by_id(db_session, UUID(garment_id))

    async def fake_semantic_search(db, *, user_id, query_vector, category, limit):
        return [(garment, 0.87)]

    monkeypatch.setattr(garment_embedding_repository, "semantic_search", fake_semantic_search)

    response = await client.post(
        "/api/v1/wardrobe/search", json={"query": "anything goes"}, headers=auth_headers
    )
    assert response.status_code == 200
    body = response.json()
    assert len(body["results"]) == 1
    assert body["results"][0]["garment"]["id"] == garment_id
    assert body["results"][0]["similarity"] == 0.87
