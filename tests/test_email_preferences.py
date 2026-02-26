"""
Test script for multi-user email preferences and delivery.
"""
import asyncio
from httpx import AsyncClient
from app.main import app

USERS = [
    {"email": "user1@example.com", "password": "Testpass1!", "prefs": {"email_frequency": "immediate"}},
    {"email": "user2@example.com", "password": "Testpass2!", "prefs": {"email_frequency": "daily_digest"}},
    {"email": "user3@example.com", "password": "Testpass3!", "prefs": {"email_frequency": "off"}},
]

async def register_and_set_prefs(client, user):
    # Register
    await client.post("/api/auth/register", json={"email": user["email"], "password": user["password"]})
    # Login
    resp = await client.post("/api/auth/login", json={"email": user["email"], "password": user["password"]})
    token = resp.json()["access_token"]
    # Set preferences
    await client.patch(
        "/api/auth/profile",
        json={"preferences": user["prefs"]},
        headers={"Authorization": f"Bearer {token}"}
    )
    return token

async def trigger_alert(client, token, title, body):
    # Simulate alert creation (replace with your actual alert endpoint)
    await client.post(
        "/api/alerts/test",
        json={"title": title, "body": body},
        headers={"Authorization": f"Bearer {token}"}
    )

async def main():
    async with AsyncClient(app=app, base_url="http://test") as client:
        tokens = []
        for user in USERS:
            token = await register_and_set_prefs(client, user)
            tokens.append(token)
        # Trigger alerts for all users
        for i, token in enumerate(tokens):
            await trigger_alert(client, token, f"Test Alert {i+1}", f"This is a test alert for user {i+1}.")
        print("Test alerts sent. Check your email inboxes and digest queues.")

if __name__ == "__main__":
    asyncio.run(main())
