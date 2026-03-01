
import pytest
from unittest.mock import patch, AsyncMock

@pytest.mark.asyncio
async def test_register_and_login_flow(client):
    """Test user registration and login flow."""
    # Register
    resp = await client.post("/auth/register", json={"email": "test@example.com", "password": "testpass123"})
    assert resp.status_code == 200
    data = resp.json()
    assert "access_token" in data and "refresh_token" in data

    # Login
    resp = await client.post("/auth/login", data={"username": "test@example.com", "password": "testpass123"})
    assert resp.status_code == 200
    data = resp.json()
    assert "access_token" in data and "refresh_token" in data

@pytest.mark.asyncio
async def test_refresh_token(client):
    """Test refresh token endpoint."""
    # Register
    resp = await client.post("/auth/register", json={"email": "refresh@example.com", "password": "refreshpass123"})
    tokens = resp.json()
    # Refresh
    resp = await client.post("/auth/refresh", json={"refresh_token": tokens["refresh_token"]})
    assert resp.status_code == 200
    data = resp.json()
    assert "access_token" in data and "refresh_token" in data

@pytest.mark.asyncio
async def test_password_reset(client, mocker):
    """Test password reset flow with secure token delivery.
    
    Security note: Token is sent via email only, not in API response.
    This test mocks email sending to capture the token.
    """
    # Register
    resp = await client.post("/auth/register", json={"email": "reset@example.com", "password": "resetpass123"})
    assert resp.status_code == 200
    
    # Mock email sending to capture token
    captured_token = None
    async def mock_send_email(to_email, subject, html_content, link=None):
        nonlocal captured_token
        # Extract token from link: /auth/reset?token=...
        if link and "token=" in link:
            captured_token = link.split("token=")[-1]
        return True
    
    mocker.patch("app.shared.utils.email_utils.send_password_reset_email", side_effect=mock_send_email)
    
    # Request reset
    resp = await client.post("/auth/password-reset/request", json={"email": "reset@example.com"})
    assert resp.status_code == 200
    reset_data = resp.json()
    
    # Verify token NOT in response (security)
    assert "reset_token" not in reset_data
    assert "email" in reset_data
    assert "message" in reset_data
    
    # Verify token was sent via email
    assert captured_token is not None, "Token should be sent via email"
    
    # Confirm reset with captured token
    resp = await client.post("/auth/password-reset/confirm", json={
        "token": captured_token,
        "new_password": "newpass123"
    })
    assert resp.status_code == 200
    assert resp.json()["success"] is True
    
    # Login with new password
    resp = await client.post("/auth/login", data={
        "username": "reset@example.com",
        "password": "newpass123"
    })
    assert resp.status_code == 200
    assert "access_token" in resp.json()

@pytest.mark.asyncio
async def test_profile_flow(client):
    """Test user profile retrieval and update."""
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
    resp = await client.patch("/auth/profile", 
        json={"telegram_id": "tg123", "preferences": {"theme": "dark"}},
        headers=headers
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["telegram_id"] == "tg123"
    assert data["preferences"]["theme"] == "dark"

@pytest.mark.asyncio
async def test_invalid_login_credentials(client):
    """Test login with invalid credentials."""
    # Try to login without registering
    resp = await client.post("/auth/login", data={
        "username": "nonexistent@example.com",
        "password": "wrongpassword"
    })
    assert resp.status_code == 401
    assert "Invalid credentials" in resp.json()["detail"]

@pytest.mark.asyncio
async def test_duplicate_email_registration(client):
    """Test registration with duplicate email."""
    # Register first user
    resp = await client.post("/auth/register", json={
        "email": "duplicate@example.com",
        "password": "password123"
    })
    assert resp.status_code == 200
    
    # Try to register with same email
    resp = await client.post("/auth/register", json={
        "email": "duplicate@example.com",
        "password": "password123"
    })
    assert resp.status_code == 400
    assert "already registered" in resp.json()["detail"].lower()

