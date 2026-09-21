import pytest
from httpx import AsyncClient

SIGNUP_PAYLOAD = {"email": "amy@example.com", "name": "Amy", "password": "correct-horse-battery"}


@pytest.mark.asyncio
async def test_signup_creates_user_and_returns_token(client: AsyncClient) -> None:
    response = await client.post("/api/v1/auth/signup", json=SIGNUP_PAYLOAD)
    assert response.status_code == 201
    body = response.json()
    assert body["token_type"] == "bearer"
    assert body["access_token"]
    assert body["user"]["email"] == SIGNUP_PAYLOAD["email"]
    assert "password" not in body["user"]


@pytest.mark.asyncio
async def test_signup_duplicate_email_rejected(client: AsyncClient) -> None:
    first = await client.post("/api/v1/auth/signup", json=SIGNUP_PAYLOAD)
    assert first.status_code == 201

    second = await client.post("/api/v1/auth/signup", json=SIGNUP_PAYLOAD)
    assert second.status_code == 409


@pytest.mark.asyncio
async def test_login_with_correct_credentials(client: AsyncClient) -> None:
    await client.post("/api/v1/auth/signup", json=SIGNUP_PAYLOAD)

    response = await client.post(
        "/api/v1/auth/login",
        json={"email": SIGNUP_PAYLOAD["email"], "password": SIGNUP_PAYLOAD["password"]},
    )
    assert response.status_code == 200
    assert response.json()["access_token"]


@pytest.mark.asyncio
async def test_login_with_wrong_password_rejected(client: AsyncClient) -> None:
    await client.post("/api/v1/auth/signup", json=SIGNUP_PAYLOAD)

    response = await client.post(
        "/api/v1/auth/login",
        json={"email": SIGNUP_PAYLOAD["email"], "password": "wrong-password"},
    )
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_login_with_unknown_email_rejected(client: AsyncClient) -> None:
    response = await client.post(
        "/api/v1/auth/login",
        json={"email": "nobody@example.com", "password": "whatever"},
    )
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_protected_route_requires_token(client: AsyncClient) -> None:
    response = await client.post("/api/v1/auth/logout")
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_protected_route_accepts_valid_token(client: AsyncClient) -> None:
    signup = await client.post("/api/v1/auth/signup", json=SIGNUP_PAYLOAD)
    token = signup.json()["access_token"]

    response = await client.post(
        "/api/v1/auth/logout", headers={"Authorization": f"Bearer {token}"}
    )
    assert response.status_code == 200


@pytest.mark.asyncio
async def test_protected_route_rejects_garbage_token(client: AsyncClient) -> None:
    response = await client.post(
        "/api/v1/auth/logout", headers={"Authorization": "Bearer not-a-real-token"}
    )
    assert response.status_code == 401
