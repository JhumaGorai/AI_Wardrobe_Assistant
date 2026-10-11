import pytest
from httpx import AsyncClient

FAKE_PNG_BYTES = b"\x89PNG\r\n\x1a\nnot-a-real-png-but-good-enough-for-these-tests"


@pytest.mark.asyncio
async def test_upload_avatar_requires_auth(client: AsyncClient) -> None:
    response = await client.post(
        "/api/v1/avatar",
        files={"file": ("avatar.png", FAKE_PNG_BYTES, "image/png")},
    )
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_upload_avatar_success(client: AsyncClient, auth_headers: dict, fake_storage) -> None:
    response = await client.post(
        "/api/v1/avatar",
        files={"file": ("avatar.png", FAKE_PNG_BYTES, "image/png")},
        data={"type": "full_body", "is_primary": "true"},
        headers=auth_headers,
    )
    assert response.status_code == 201
    body = response.json()
    assert body["type"] == "full_body"
    assert body["is_primary"] is True
    assert body["image_url"].startswith("http://fake-storage.test/")
    assert len(fake_storage.uploaded) == 1


@pytest.mark.asyncio
async def test_upload_avatar_rejects_bad_content_type(client: AsyncClient, auth_headers: dict) -> None:
    response = await client.post(
        "/api/v1/avatar",
        files={"file": ("avatar.gif", b"not-a-real-gif", "image/gif")},
        headers=auth_headers,
    )
    assert response.status_code == 415


@pytest.mark.asyncio
async def test_upload_avatar_rejects_oversized_file(client: AsyncClient, auth_headers: dict) -> None:
    too_big = b"0" * (10 * 1024 * 1024 + 1)
    response = await client.post(
        "/api/v1/avatar",
        files={"file": ("avatar.png", too_big, "image/png")},
        headers=auth_headers,
    )
    assert response.status_code == 413


@pytest.mark.asyncio
async def test_second_primary_avatar_unsets_first(client: AsyncClient, auth_headers: dict) -> None:
    first = await client.post(
        "/api/v1/avatar",
        files={"file": ("first.png", FAKE_PNG_BYTES, "image/png")},
        data={"is_primary": "true"},
        headers=auth_headers,
    )
    second = await client.post(
        "/api/v1/avatar",
        files={"file": ("second.png", FAKE_PNG_BYTES, "image/png")},
        data={"is_primary": "true"},
        headers=auth_headers,
    )
    assert first.status_code == 201
    assert second.status_code == 201

    listing = await client.get("/api/v1/avatar", headers=auth_headers)
    avatars = listing.json()
    assert len(avatars) == 2
    primary_flags = {a["id"]: a["is_primary"] for a in avatars}
    assert primary_flags[second.json()["id"]] is True
    assert primary_flags[first.json()["id"]] is False


@pytest.mark.asyncio
async def test_avatars_are_isolated_per_user(client: AsyncClient, auth_headers: dict) -> None:
    await client.post(
        "/api/v1/avatar",
        files={"file": ("mine.png", FAKE_PNG_BYTES, "image/png")},
        headers=auth_headers,
    )

    signup_b = await client.post(
        "/api/v1/auth/signup",
        json={"email": "avatar-user-b@example.com", "name": "B", "password": "correct-horse-battery"},
    )
    headers_b = {"Authorization": f"Bearer {signup_b.json()['access_token']}"}

    listing_b = await client.get("/api/v1/avatar", headers=headers_b)
    assert listing_b.json() == []
