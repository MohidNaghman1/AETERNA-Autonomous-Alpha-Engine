import time
"""
Integration tests for event processing, alert generation, and alert API endpoints.
"""
import pytest
from fastapi.testclient import TestClient
from app.modules.alerting.presentation.alerts import router, ALERT_STORE
from app.modules.alerting.application.alert_generator import generate_alert, user_alert_times
from app.modules.intelligence.application.agent_a import score_event

from fastapi import FastAPI

@pytest.fixture(autouse=True)
def clear_alert_store():
    ALERT_STORE.clear()
    user_alert_times.clear()
    yield
    ALERT_STORE.clear()
    user_alert_times.clear()

def get_test_app():
    app = FastAPI()
    app.include_router(router)
    return app

# --- Test data ---
USER_ID = "user123"
EVENT = {
    "id": "evt1",
    "user_id": USER_ID,
    "sources": ["a", "b", "c"],
    "engagement_rate": 0.1,
    "verified": True,
    "username": "realuser",
    "text": "Breaking news!",
    "embedding": [0.1]*10,
}
USER_PREFS = {"channels": ["web", "telegram"], "quiet_hours": {"start": "22:00", "end": "07:00"}}

# --- Integration test: scoring + alert generation ---
def test_scoring_and_alert_generation():
    result = score_event(EVENT, db_embeddings=[])
    assert result["priority"] == "HIGH"
    alert = generate_alert({**EVENT, **result}, USER_PREFS)
    assert alert is not None
    assert set(alert["channels"]) == {"web", "telegram"}
    assert alert["priority"] == "HIGH"

# --- Integration test: API endpoints ---
def test_alert_api_endpoints():
    app = get_test_app()
    client = TestClient(app)
    # Generate and store alert
    result = score_event(EVENT, db_embeddings=[])
    alert = generate_alert({**EVENT, **result}, USER_PREFS)
    ALERT_STORE[alert["alert_id"]] = alert
    # List alerts
    resp = client.get("/api/alerts/", params={"user_id": USER_ID})
    assert resp.status_code == 200
    assert len(resp.json()) == 1
    # Get alert detail
    resp = client.get(f"/api/alerts/{alert['alert_id']}", params={"user_id": USER_ID})
    assert resp.status_code == 200
    # Mark as read
    resp = client.patch(f"/api/alerts/{alert['alert_id']}", params={"user_id": USER_ID})
    assert resp.status_code == 200
    assert resp.json()["status"] == "read"
    # Dismiss
    resp = client.delete(f"/api/alerts/{alert['alert_id']}", params={"user_id": USER_ID})
    assert resp.status_code == 200
    assert resp.json()["detail"] == "Alert dismissed"

# --- Integration test: rate limiting and quiet hours ---
# --- Integration test: rate limiting and quiet hours ---
def test_rate_limiting_and_quiet_hours():
    # Simulate 10 alerts in the last hour
    for _ in range(10):
        alert = generate_alert({**EVENT, "id": f"evt{_}", "priority": "HIGH", "score": 90}, USER_PREFS)
        assert alert is not None
    # 11th alert should be rate limited
    alert = generate_alert({**EVENT, "id": "evt11", "priority": "HIGH", "score": 90}, USER_PREFS)
    assert alert is None
    # Quiet hours (simulate time)
    prefs = {"channels": ["web"], "quiet_hours": {"start": "00:00", "end": "23:59"}}
    alert = generate_alert({**EVENT, "id": "evt12", "priority": "HIGH", "score": 90}, prefs)
    assert alert is None


# --- Performance test: 100+ events/sec ---
def test_performance_100_events_per_sec():
    num_events = 1000
    events = []
    for i in range(num_events):
        e = {**EVENT, "id": f"evt{i}", "embedding": [float(i % 10)] * 10}
        events.append(e)
    start = time.time()
    results = []
    for e in events:
        result = score_event(e, db_embeddings=[])
        alert = generate_alert({**e, **result}, USER_PREFS)
        results.append(alert)
    elapsed = time.time() - start
    throughput = num_events / elapsed
    print(f"Throughput: {throughput:.2f} events/sec")
    assert throughput >= 100, f"Throughput below target: {throughput:.2f} events/sec"
