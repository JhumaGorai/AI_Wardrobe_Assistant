import pytest
from httpx import AsyncClient

from app.core.deps_processing import get_garment_processor
from app.core.image_validation import MAX_IMAGE_SIZE_BYTES
from app.main import app
from app.schemas.garment import ALLOWED_CATEGORIES, GarmentAnalysis
from app.services.garment_processor import process_garment

pytestmark = pytest.mark.asyncio


def _image_file(name: str = "shirt.jpg", content: bytes = b"fake-image-bytes", content_type: str = "image/jpeg"):
    return {"file": (name, content, content_type)}


class _AlwaysFailingVisionService:
    async def analyze_garment(self, image_url: str) -> GarmentAnalysis:
        raise RuntimeError("simulated vision provider outage -- should never reach the client")


async def test_upload_requires_auth(client: AsyncClient):
    response = await client.post("/api/v1/garments", files=_image_file())
    assert response.status_code == 401


async def test_upload_creates_pending_garment_then_background_processing_completes(
    client: AsyncClient, auth_headers: dict[str, str]
):
    upload_response = await client.post(
        "/api/v1/garments", files=_image_file(), data={"name": "Favorite shirt"}, headers=auth_headers
    )
    assert upload_response.status_code == 201
    body = upload_response.json()
    # Response must come back before analysis runs (Phase 6: "should not block on a slow AI
    # provider") -- so at this point it must still be pending, not completed.
    assert body["processing_status"] == "pending"
    assert body["name"] == "Favorite shirt"
    assert len(body["images"]) == 1
    assert body["images"][0]["image_url"].startswith("http://fake-storage.test/")

    garment_id = body["id"]
    get_response = await client.get(f"/api/v1/garments/{garment_id}", headers=auth_headers)
    assert get_response.status_code == 200
    processed = get_response.json()
    # By the time the background task (scheduled during the POST above) has run, this should
    # already reflect the mock vision analysis.
    assert processed["processing_status"] == "completed"
    assert processed["processing_error"] is None
    assert processed["category"] in ALLOWED_CATEGORIES
    assert isinstance(processed["colors"], list) and len(processed["colors"]) > 0
    assert processed["description"]


async def test_upload_rejects_unsupported_content_type(client: AsyncClient, auth_headers: dict[str, str]):
    response = await client.post(
        "/api/v1/garments",
        files=_image_file(name="shirt.gif", content=b"gif-bytes", content_type="image/gif"),
        headers=auth_headers,
    )
    assert response.status_code == 415


async def test_upload_rejects_oversized_file(client: AsyncClient, auth_headers: dict[str, str]):
    oversized = b"x" * (MAX_IMAGE_SIZE_BYTES + 1)
    response = await client.post(
        "/api/v1/garments", files=_image_file(content=oversized), headers=auth_headers
    )
    assert response.status_code == 413


async def test_upload_rejects_empty_file(client: AsyncClient, auth_headers: dict[str, str]):
    response = await client.post(
        "/api/v1/garments", files=_image_file(content=b""), headers=auth_headers
    )
    assert response.status_code == 400


async def test_get_garment_not_found_for_other_user(client: AsyncClient, auth_headers: dict[str, str]):
    upload_response = await client.post("/api/v1/garments", files=_image_file(), headers=auth_headers)
    garment_id = upload_response.json()["id"]

    other_signup = await client.post(
        "/api/v1/auth/signup",
        json={"email": "other-user@example.com", "name": "Other", "password": "another-password"},
    )
    other_headers = {"Authorization": f"Bearer {other_signup.json()['access_token']}"}

    get_response = await client.get(f"/api/v1/garments/{garment_id}", headers=other_headers)
    assert get_response.status_code == 404

    put_response = await client.put(
        f"/api/v1/garments/{garment_id}", json={"name": "hijacked"}, headers=other_headers
    )
    assert put_response.status_code == 404

    delete_response = await client.delete(f"/api/v1/garments/{garment_id}", headers=other_headers)
    assert delete_response.status_code == 404


async def test_update_garment_applies_partial_fields(client: AsyncClient, auth_headers: dict[str, str]):
    upload_response = await client.post("/api/v1/garments", files=_image_file(), headers=auth_headers)
    garment_id = upload_response.json()["id"]

    update_response = await client.put(
        f"/api/v1/garments/{garment_id}",
        json={"name": "Corrected name", "category": "outerwear"},
        headers=auth_headers,
    )
    assert update_response.status_code == 200
    updated = update_response.json()
    assert updated["name"] == "Corrected name"
    assert updated["category"] == "outerwear"

    # Unrelated fields filled in by background processing must survive the partial update.
    assert updated["description"]


async def test_update_rejects_invalid_category(client: AsyncClient, auth_headers: dict[str, str]):
    upload_response = await client.post("/api/v1/garments", files=_image_file(), headers=auth_headers)
    garment_id = upload_response.json()["id"]

    response = await client.put(
        f"/api/v1/garments/{garment_id}", json={"category": "not-a-real-category"}, headers=auth_headers
    )
    assert response.status_code == 422


async def test_delete_garment_is_soft_delete(client: AsyncClient, auth_headers: dict[str, str]):
    upload_response = await client.post("/api/v1/garments", files=_image_file(), headers=auth_headers)
    garment_id = upload_response.json()["id"]

    delete_response = await client.delete(f"/api/v1/garments/{garment_id}", headers=auth_headers)
    assert delete_response.status_code == 204
    # A 204 response must have NO body at all (HTTP spec) -- returning a bare `None` from the
    # route still serializes it as a literal "null" JSON body, which real browsers can reject
    # even though httpx's ASGI transport (used here) lets it through uncomplaining. Pin this
    # down explicitly so this regression can't come back silently.
    assert delete_response.content == b""
    assert "content-type" not in delete_response.headers

    get_response = await client.get(f"/api/v1/garments/{garment_id}", headers=auth_headers)
    assert get_response.status_code == 404


async def test_processing_failure_sets_failed_status_with_safe_error(
    client: AsyncClient, auth_headers: dict[str, str], db_session
):
    async def failing_processor(garment_id):
        await process_garment(garment_id, db_session, _AlwaysFailingVisionService())

    app.dependency_overrides[get_garment_processor] = lambda: failing_processor

    upload_response = await client.post("/api/v1/garments", files=_image_file(), headers=auth_headers)
    garment_id = upload_response.json()["id"]

    get_response = await client.get(f"/api/v1/garments/{garment_id}", headers=auth_headers)
    body = get_response.json()
    assert body["processing_status"] == "failed"
    assert body["processing_error"] is not None
    assert "simulated" not in body["processing_error"]
    assert "RuntimeError" not in body["processing_error"]


async def test_list_garments_only_returns_own_active_garments(
    client: AsyncClient, auth_headers: dict[str, str]
):
    first = await client.post(
        "/api/v1/garments", files=_image_file(), data={"name": "First"}, headers=auth_headers
    )
    await client.post(
        "/api/v1/garments", files=_image_file(), data={"name": "Second"}, headers=auth_headers
    )
    first_id = first.json()["id"]

    # Soft-deleted garments must not appear in the list.
    await client.delete(f"/api/v1/garments/{first_id}", headers=auth_headers)

    other_signup = await client.post(
        "/api/v1/auth/signup",
        json={"email": "wardrobe-other@example.com", "name": "Other", "password": "another-password"},
    )
    other_headers = {"Authorization": f"Bearer {other_signup.json()['access_token']}"}
    await client.post(
        "/api/v1/garments", files=_image_file(), data={"name": "Not mine"}, headers=other_headers
    )

    list_response = await client.get("/api/v1/garments", headers=auth_headers)
    assert list_response.status_code == 200
    names = [g["name"] for g in list_response.json()]
    assert names == ["Second"]
