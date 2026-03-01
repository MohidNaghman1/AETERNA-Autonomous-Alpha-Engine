"""Test script for multi-user email preferences and delivery.

Tests that user email preferences are correctly stored and retrievable.
"""
import pytest
from httpx import AsyncClient

# Test data
USERS = [
    {"email": "user1@example.com", "password": "Testpass1!", "prefs": {"email_frequency": "immediate"}},
    {"email": "user2@example.com", "password": "Testpass2!", "prefs": {"email_frequency": "daily_digest"}},
    {"email": "user3@example.com", "password": "Testpass3!", "prefs": {"email_frequency": "off"}},
]

@pytest.mark.asyncio
async def test_register_and_set_email_preferences(client):
    """Test registering users and setting email preferences."""
    for user in USERS:
        # Register
        resp = await client.post("/auth/register", json={
            "email": user["email"],
            "password": user["password"]
        })
        assert resp.status_code == 200, f"Failed to register {user['email']}"
        tokens = resp.json()
        
        # Get initial profile
        headers = {"Authorization": f"Bearer {tokens['access_token']}"}
        resp = await client.get("/auth/profile", headers=headers)
        assert resp.status_code == 200
        profile = resp.json()
        assert profile["email"] == user["email"]
        
        # Set preferences
        resp = await client.patch("/auth/profile", 
            json={"preferences": user["prefs"]},
            headers=headers
        )
        assert resp.status_code == 200
        updated_profile = resp.json()
        assert updated_profile["preferences"]["email_frequency"] == user["prefs"]["email_frequency"]

@pytest.mark.asyncio
async def test_email_frequency_preferences(client):
    """Test different email frequency preferences."""
    preferences = [
        {"email_frequency": "immediate", "expected_behavior": "Alert sent immediately"},
        {"email_frequency": "daily_digest", "expected_behavior": "Alerts batched daily"},
        {"email_frequency": "off", "expected_behavior": "No emails sent"},
    ]
    
    for i, pref in enumerate(preferences):
        email = f"freq_test_{i}@example.com"
        
        # Register user
        resp = await client.post("/auth/register", json={
            "email": email,
            "password": "password123"
        })
        assert resp.status_code == 200
        tokens = resp.json()
        headers = {"Authorization": f"Bearer {tokens['access_token']}"}
        
        # Set preference
        resp = await client.patch("/auth/profile",
            json={"preferences": {"email_frequency": pref["email_frequency"]}},
            headers=headers
        )
        assert resp.status_code == 200
        
        # Verify it was saved
        resp = await client.get("/auth/profile", headers=headers)
        assert resp.status_code == 200
        saved_pref = resp.json()["preferences"]["email_frequency"]
        assert saved_pref == pref["email_frequency"]

@pytest.mark.asyncio
async def test_update_preferences_multiple_times(client):
    """Test updating preferences multiple times."""
    email = "update_test@example.com"
    
    # Register
    resp = await client.post("/auth/register", json={
        "email": email,
        "password": "password123"
    })
    tokens = resp.json()
    headers = {"Authorization": f"Bearer {tokens['access_token']}"}
    
    # Update to immediate
    resp = await client.patch("/auth/profile",
        json={"preferences": {"email_frequency": "immediate"}},
        headers=headers
    )
    assert resp.status_code == 200
    assert resp.json()["preferences"]["email_frequency"] == "immediate"
    
    # Update to daily_digest
    resp = await client.patch("/auth/profile",
        json={"preferences": {"email_frequency": "daily_digest"}},
        headers=headers
    )
    assert resp.status_code == 200
    assert resp.json()["preferences"]["email_frequency"] == "daily_digest"
    
    # Update to off
    resp = await client.patch("/auth/profile",
        json={"preferences": {"email_frequency": "off"}},
        headers=headers
    )
    assert resp.status_code == 200
    assert resp.json()["preferences"]["email_frequency"] == "off"

