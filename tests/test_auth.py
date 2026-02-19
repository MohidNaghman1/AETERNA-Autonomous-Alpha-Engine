
import pytest

@pytest.mark.asyncio
async def test_register_and_login_flow(client):
    # Register
    resp = await client.post("/auth/register", json={"email": "test@example.com", "password": "testpass123"})
    assert resp.status_code == 200
    data = resp.json()
    assert "access_token" in data and "refresh_token" in data

    # Login
    resp = await client.post("/auth/login", json={"email": "test@example.com", "password": "testpass123"})
    assert resp.status_code == 200
    data = resp.json()
    assert "access_token" in data and "refresh_token" in data

@pytest.mark.asyncio
async def test_refresh_token(client):
    # Register
    resp = await client.post("/auth/register", json={"email": "refresh@example.com", "password": "refreshpass123"})
    tokens = resp.json()
    # Refresh
    resp = await client.post("/auth/refresh", json={"refresh_token": tokens["refresh_token"]})
    assert resp.status_code == 200
    data = resp.json()
    assert "access_token" in data and "refresh_token" in data

@pytest.mark.asyncio
async def test_password_reset(client):
    # Register
    await client.post("/auth/register", json={"email": "reset@example.com", "password": "resetpass123"})
    # Request reset
    resp = await client.post("/auth/password-reset/request", json={"email": "reset@example.com"})
    assert resp.status_code == 200
    reset_data = resp.json()
    # Confirm reset
    resp = await client.post("/auth/password-reset/confirm", json={"token": reset_data["reset_token"], "new_password": "newpass123"})
    assert resp.status_code == 200
    assert resp.json()["success"]
    # Login with new password
    resp = await client.post("/auth/login", json={"email": "reset@example.com", "password": "newpass123"})
    assert resp.status_code == 200

@pytest.mark.asyncio
async def test_profile_flow(client):
    # Register
    resp = await client.post("/auth/register", json={"email": "profile@example.com", "password": "profilepass123"})
    tokens = resp.json()
    headers = {"Authorization": f"Bearer {tokens['access_token']}"}
    # Get profile
    resp = await client.get("/auth/profile", headers=headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["email"] == "profile@example.com"
    # Update profile
    resp = await client.patch("/auth/profile", json={"telegram_id": "tg123", "preferences": {"theme": "dark"}}, headers=headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["telegram_id"] == "tg123"
    assert data["preferences"]["theme"] == "dark"
