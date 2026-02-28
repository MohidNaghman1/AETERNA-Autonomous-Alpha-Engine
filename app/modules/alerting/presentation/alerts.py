
"""
Alert API endpoints for listing, retrieving, marking as read, and dismissing alerts.
"""

import csv
from fastapi.responses import StreamingResponse
from io import StringIO
from fastapi import APIRouter, HTTPException, Query
from typing import List, Optional
from app.modules.alerting.presentation.schema import Alert, AlertDismissResponse
from datetime import datetime, timedelta

router = APIRouter(prefix="/api/alerts", tags=["alerts"])

# In-memory alert store for demo (replace with DB in production)
ALERT_STORE = {}


@router.get("/history", response_model=List[Alert])
def alert_history(
    user_id: str = Query(...),
    start_date: Optional[str] = Query(None),
    end_date: Optional[str] = Query(None),
    priority: Optional[str] = Query(None),
    entity: Optional[str] = Query(None),
    search: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
):
    """Get alert history for last 30 days with filters, pagination, and search."""
    now = datetime.utcnow()
    min_date = now - timedelta(days=30)
    alerts = [a for a in ALERT_STORE.values() if a["user_id"] == user_id]
    # Date filter
    def parse_dt(dt):
        try:
            return datetime.fromisoformat(dt)
        except:
            return None
    if start_date:
        sd = parse_dt(start_date)
        if sd:
            alerts = [a for a in alerts if datetime.fromisoformat(a["created_at"]) >= sd]
    else:
        alerts = [a for a in alerts if datetime.fromisoformat(a["created_at"]) >= min_date]
    if end_date:
        ed = parse_dt(end_date)
        if ed:
            alerts = [a for a in alerts if datetime.fromisoformat(a["created_at"]) <= ed]
    # Priority filter
    if priority:
        alerts = [a for a in alerts if a.get("priority") == priority]
    # Entity filter
    if entity:
        alerts = [a for a in alerts if a.get("entity") == entity]
    # Search (simple full-text)
    if search:
        s = search.lower()
        alerts = [a for a in alerts if s in str(a).lower()]
    # Sort by created_at desc
    alerts.sort(key=lambda a: a["created_at"], reverse=True)
    # Pagination
    start = (page - 1) * page_size
    end = start + page_size
    return alerts[start:end]

@router.get("/{alert_id}", response_model=Alert)
def get_alert(alert_id: str, user_id: str = Query(...)):
    alert = ALERT_STORE.get(alert_id)
    if not alert or alert["user_id"] != user_id:
        raise HTTPException(status_code=404, detail="Alert not found")
    return alert

@router.patch("/{alert_id}", response_model=Alert)
def mark_alert_read(alert_id: str, user_id: str = Query(...)):
    alert = ALERT_STORE.get(alert_id)
    if not alert or alert["user_id"] != user_id:
        raise HTTPException(status_code=404, detail="Alert not found")
    alert["status"] = "read"
    alert["read_at"] = datetime.utcnow().isoformat()
    return alert

@router.delete("/{alert_id}", response_model=AlertDismissResponse)
def dismiss_alert(alert_id: str, user_id: str = Query(...)):
    alert = ALERT_STORE.get(alert_id)
    if not alert or alert["user_id"] != user_id:
        raise HTTPException(status_code=404, detail="Alert not found")
    del ALERT_STORE[alert_id]
    return {"detail": "Alert dismissed"}

# To use: include_router(router) in your FastAPI app

# CSV export endpoint
@router.get("/history/export", response_class=StreamingResponse)
def export_alert_history_csv(
    user_id: str = Query(...),
    start_date: Optional[str] = Query(None),
    end_date: Optional[str] = Query(None),
    priority: Optional[str] = Query(None),
    entity: Optional[str] = Query(None),
    search: Optional[str] = Query(None),
):
    """Export alert history as CSV (last 30 days, filters supported)."""
    # Reuse filtering logic from alert_history
    now = datetime.utcnow()
    min_date = now - timedelta(days=30)
    alerts = [a for a in ALERT_STORE.values() if a["user_id"] == user_id]
    def parse_dt(dt):
        try:
            return datetime.fromisoformat(dt)
        except:
            return None
    if start_date:
        sd = parse_dt(start_date)
        if sd:
            alerts = [a for a in alerts if datetime.fromisoformat(a["created_at"]) >= sd]
    else:
        alerts = [a for a in alerts if datetime.fromisoformat(a["created_at"]) >= min_date]
    if end_date:
        ed = parse_dt(end_date)
        if ed:
            alerts = [a for a in alerts if datetime.fromisoformat(a["created_at"]) <= ed]
    if priority:
        alerts = [a for a in alerts if a.get("priority") == priority]
    if entity:
        alerts = [a for a in alerts if a.get("entity") == entity]
    if search:
        s = search.lower()
        alerts = [a for a in alerts if s in str(a).lower()]
    # Sort by created_at desc
    alerts.sort(key=lambda a: a["created_at"], reverse=True)
    # CSV streaming
    def iter_csv():
        if not alerts:
            yield "alert_id,created_at,title,priority,entity,status\n"
            return
        fieldnames = ["alert_id", "created_at", "title", "priority", "entity", "status"]
        buf = StringIO()
        writer = csv.DictWriter(buf, fieldnames=fieldnames)
        writer.writeheader()
        for a in alerts:
            row = {k: a.get(k, "") for k in fieldnames}
            writer.writerow(row)
        buf.seek(0)
        yield buf.read()
    return StreamingResponse(iter_csv(), media_type="text/csv", headers={"Content-Disposition": "attachment; filename=alerts.csv"})
