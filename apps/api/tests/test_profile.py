import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_get_profile_before_creation_returns_404(client: AsyncClient, auth_headers: dict) -> None:
    response = await client.get("/api/v1/profile", headers=auth_headers)
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_put_profile_creates_it(client: AsyncClient, auth_headers: dict) -> None:
    payload = {
        "height_cm": 170,
        "body_shape": "hourglass",
        "preferred_fit": "relaxed",
        "preferred_styles": ["minimalist"],
        "preferred_colors": ["black", "cream"],
        "disliked_colors": ["orange"],
        "style_preferences": {"loves_layers": True},
    }
    response = await client.put("/api/v1/profile", json=payload, headers=auth_headers)
    assert response.status_code == 200
    body = response.json()
    assert body["height_cm"] == 170
    assert body["preferred_styles"] == ["minimalist"]

    # And it persists / is now gettable.
    get_response = await client.get("/api/v1/profile", headers=auth_headers)
    assert get_response.status_code == 200
    assert get_response.json()["body_shape"] == "hourglass"


@pytest.mark.asyncio
async def test_put_profile_updates_existing(client: AsyncClient, auth_headers: dict) -> None:
    await client.put("/api/v1/profile", json={"preferred_fit": "regular"}, headers=auth_headers)
    response = await client.put("/api/v1/profile", json={"preferred_fit": "oversized"}, headers=auth_headers)
    assert response.status_code == 200
    assert response.json()["preferred_fit"] == "oversized"


@pytest.mark.asyncio
async def test_profile_requires_auth(client: AsyncClient) -> None:
    get_response = await client.get("/api/v1/profile")
    assert get_response.status_code == 401

    put_response = await client.put("/api/v1/profile", json={"preferred_fit": "regular"})
    assert put_response.status_code == 401


@pytest.mark.asyncio
async def test_height_cm_out_of_range_rejected(client: AsyncClient, auth_headers: dict) -> None:
    response = await client.put("/api/v1/profile", json={"height_cm": 10}, headers=auth_headers)
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_profile_is_isolated_per_user(client: AsyncClient, auth_headers: dict) -> None:
    await client.put("/api/v1/profile", json={"body_shape": "user-a-shape"}, headers=auth_headers)

    signup_b = await client.post(
        "/api/v1/auth/signup",
        json={"email": "user-b@example.com", "name": "B", "password": "correct-horse-battery"},
    )
    headers_b = {"Authorization": f"Bearer {signup_b.json()['access_token']}"}

    # User B has no profile yet — must not see user A's.
    response = await client.get("/api/v1/profile", headers=headers_b)
    assert response.status_code == 404
