"""
Ingestion module API router with enhanced filtering.
"""

from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import desc, and_, func
from app.shared.application.dependencies import get_db
from app.modules.ingestion.infrastructure.models import EventORM
from app.modules.ingestion.presentation.schemas import EventIn, EventOut
from typing import List, Optional
from datetime import datetime
import logging

router = APIRouter()
logger = logging.getLogger(__name__)


# Example endpoint (health check for ingestion)
@router.get("/health")
def ingestion_health():
    return {"status": "ok"}


@router.post("/events", response_model=EventOut, status_code=201)
async def create_event(event: EventIn, db: AsyncSession = Depends(get_db)):
    """Create an event directly via API."""
    try:
        db_event = EventORM(**event.dict())
        db.add(db_event)
        await db.commit()
        await db.refresh(db_event)
        logger.info(f"[✅ API] Event created: {db_event.id}")
        return db_event
    except Exception as e:
        await db.rollback()
        logger.error(f"[❌ API] Failed to create event: {str(e)}")
        raise HTTPException(status_code=400, detail=f"Failed to store event: {e}")


@router.get("/events/{event_id}", response_model=EventOut)
async def get_event(event_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(EventORM).where(EventORM.id == event_id))
    event = result.scalar_one_or_none()
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")
    return event


@router.get("/events", response_model=List[EventOut])
async def list_events(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    source: Optional[str] = None,
    type: Optional[str] = None,
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    db: AsyncSession = Depends(get_db),
):
    """
    List events with optional filtering.

    Query Parameters:
    - skip: Offset for pagination (default: 0)
    - limit: Number of events to return (default: 100, max: 500)
    - source: Filter by source (e.g., "coindesk", "coingecko")
    - type: Filter by type (e.g., "news", "price")
    - start_date: Filter events after this date (ISO format)
    - end_date: Filter events before this date (ISO format)
    """
    query = select(EventORM)

    # Apply filters
    filters = []
    if source:
        filters.append(EventORM.source == source)
    if type:
        filters.append(EventORM.type == type)
    if start_date:
        filters.append(EventORM.timestamp >= start_date)
    if end_date:
        filters.append(EventORM.timestamp <= end_date)

    if filters:
        query = query.where(and_(*filters))

    # Order by timestamp descending, apply pagination
    result = await db.execute(
        query.order_by(desc(EventORM.timestamp)).offset(skip).limit(limit)
    )
    events = result.scalars().all()
    return events


@router.get("/search/by-source/{source}", response_model=List[EventOut])
async def list_events_by_source(
    source: str,
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    db: AsyncSession = Depends(get_db),
):
    """Filter events by source (e.g., coindesk, coingecko)."""
    result = await db.execute(
        select(EventORM)
        .where(EventORM.source == source)
        .order_by(desc(EventORM.timestamp))
        .offset(skip)
        .limit(limit)
    )
    events = result.scalars().all()
    return events


@router.get("/search/by-type/{event_type}", response_model=List[EventOut])
async def list_events_by_type(
    event_type: str,
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    db: AsyncSession = Depends(get_db),
):
    """Filter events by type (news or price)."""
    result = await db.execute(
        select(EventORM)
        .where(EventORM.type == event_type)
        .order_by(desc(EventORM.timestamp))
        .offset(skip)
        .limit(limit)
    )
    events = result.scalars().all()
    return events


@router.get("/stats")
async def get_ingestion_stats(db: AsyncSession = Depends(get_db)):
    """Get statistics about ingested events."""
    # Count total events
    total_result = await db.execute(select(func.count(EventORM.id)))
    total = total_result.scalar() or 0

    # Count by source
    source_result = await db.execute(
        select(EventORM.source, func.count(EventORM.id)).group_by(EventORM.source)
    )
    sources = {row[0]: row[1] for row in source_result.all()}

    # Count by type
    type_result = await db.execute(
        select(EventORM.type, func.count(EventORM.id)).group_by(EventORM.type)
    )
    types = {row[0]: row[1] for row in type_result.all()}

    return {"total_events": total, "by_source": sources, "by_type": types}


@router.get("/auto-update-status")
async def auto_update_status(db: AsyncSession = Depends(get_db)):
    """Check if automatic updates are running.

    Returns:
    - auto_updates_enabled: True if scheduler is running
    - update_frequency: How often news is fetched
    - last_event_time: Timestamp of most recent event in database
    """
    try:
        from app.main import background_scheduler

        # Get latest event timestamp
        latest_result = await db.execute(
            select(EventORM.timestamp).order_by(desc(EventORM.timestamp)).limit(1)
        )
        latest_event = latest_result.scalar()
        last_event_time = latest_event.isoformat() if latest_event else None

        # Check scheduler status
        scheduler_running = background_scheduler and background_scheduler.running

        return {
            "status": "active" if scheduler_running else "inactive",
            "auto_updates_enabled": scheduler_running,
            "update_frequency": {
                "rss_collection": "every 60 seconds",
                "consumer_processing": "every 3 seconds (50 messages per batch)",
                "price_collection": "every 120 seconds",
            },
            "last_event_timestamp": last_event_time,
            "message": (
                "🔄 Automatic updates RUNNING - new events fetched every 60 seconds"
                if scheduler_running
                else "⚠️  Scheduler not running"
            ),
        }
    except Exception as e:
        logger.error(f"[AUTO-UPDATE] Status check failed: {e}")
        return {"status": "error", "auto_updates_enabled": False, "error": str(e)}
