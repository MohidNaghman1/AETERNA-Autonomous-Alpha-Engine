"""
Alert API endpoints for listing, retrieving, marking as read, and dismissing alerts.
"""
from fastapi import APIRouter, HTTPException, Query
from typing import List, Optional
from datetime import datetime

router = APIRouter(prefix="/api/alerts", tags=["alerts"])

# In-memory alert store for demo (replace with DB in production)
ALERT_STORE = {}

@router.get("/", response_model=List[dict])
def list_alerts(user_id: str = Query(...)):
    """List all alerts for a user."""
    return [a for a in ALERT_STORE.values() if a["user_id"] == user_id]

@router.get("/{alert_id}", response_model=dict)
def get_alert(alert_id: str, user_id: str = Query(...)):
    alert = ALERT_STORE.get(alert_id)
    if not alert or alert["user_id"] != user_id:
        raise HTTPException(status_code=404, detail="Alert not found")
    return alert

@router.patch("/{alert_id}", response_model=dict)
def mark_alert_read(alert_id: str, user_id: str = Query(...)):
    alert = ALERT_STORE.get(alert_id)
    if not alert or alert["user_id"] != user_id:
        raise HTTPException(status_code=404, detail="Alert not found")
    alert["status"] = "read"
    alert["read_at"] = datetime.utcnow().isoformat()
    return alert

@router.delete("/{alert_id}", response_model=dict)
def dismiss_alert(alert_id: str, user_id: str = Query(...)):
    alert = ALERT_STORE.get(alert_id)
    if not alert or alert["user_id"] != user_id:
        raise HTTPException(status_code=404, detail="Alert not found")
    del ALERT_STORE[alert_id]
    return {"detail": "Alert dismissed"}

# To use: include_router(router) in your FastAPI app
