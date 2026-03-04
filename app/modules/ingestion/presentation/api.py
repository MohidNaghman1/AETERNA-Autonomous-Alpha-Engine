"""
Ingestion module API router with enhanced filtering.
"""

from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import desc, and_, func
from app.shared.application.dependencies import get_db
from app.modules.ingestion.infrastructure.models import EventORM
from .schemas import EventIn, EventOut
from typing import List, Optional
from datetime import datetime
import os
import logging

router = APIRouter()
logger = logging.getLogger(__name__)


# Example endpoint (health check for ingestion)
@router.get("/health")
def ingestion_health():
    return {"status": "ok"}


@router.get("/diagnostic")
async def diagnostic_check(db: AsyncSession = Depends(get_db)):
    """
    Comprehensive diagnostic endpoint to check:
    - Database connectivity
    - RabbitMQ connectivity
    - Event table status
    """
    diagnostics = {
        "timestamp": datetime.utcnow().isoformat(),
        "database": {},
        "rabbitmq": {},
        "events": {},
    }

    # Test database
    try:
        result = await db.execute(select(func.count(EventORM.id)))
        total_events = result.scalar() or 0
        diagnostics["database"]["status"] = "✅ Connected"
        diagnostics["database"]["total_events"] = total_events

        # Get recent events
        recent = await db.execute(
            select(EventORM)
            .order_by(desc(EventORM.timestamp))
            .limit(3)
        )
        recent_events = recent.scalars().all()
        diagnostics["events"]["recent"] = [
            {
                "id": e.id,
                "source": e.source,
                "type": e.type,
                "timestamp": e.timestamp.isoformat() if e.timestamp else None,
            }
            for e in recent_events
        ]
    except Exception as e:
        diagnostics["database"]["status"] = f"❌ Error: {str(e)}"
        diagnostics["database"]["total_events"] = None

    # Test RabbitMQ
    try:
        import pika

        host = os.getenv("RABBITMQ_HOST", "localhost")
        user = os.getenv("RABBITMQ_USER", "guest")
        password = os.getenv("RABBITMQ_PASSWORD", "guest")

        credentials = pika.PlainCredentials(user, password)
        conn = pika.BlockingConnection(
            pika.ConnectionParameters(
                host=host, credentials=credentials, connection_attempts=1
            )
        )
        channel = conn.channel()
        conn.close()
        diagnostics["rabbitmq"]["status"] = "✅ Connected"
        diagnostics["rabbitmq"]["host"] = host
    except Exception as e:
        diagnostics["rabbitmq"]["status"] = f"❌ Error: {str(e)}"
        diagnostics["rabbitmq"]["host"] = os.getenv("RABBITMQ_HOST", "localhost")

    return diagnostics


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


@router.post("/test-event")
async def create_test_event(db: AsyncSession = Depends(get_db)):
    """Create a test event to verify database storage works."""
    try:
        test_event = EventORM(
            source="test",
            type="test",
            timestamp=datetime.utcnow(),
            content={"title": "Test Event", "message": "This is a test event"},
            raw=None,
        )
        db.add(test_event)
        await db.commit()
        await db.refresh(test_event)
        logger.info(f"[✅ TEST] Test event created: {test_event.id}")
        return {
            "status": "success",
            "event_id": test_event.id,
            "timestamp": test_event.timestamp.isoformat(),
        }
    except Exception as e:
        await db.rollback()
        logger.error(f"[❌ TEST] Failed to create test event: {str(e)}")
        raise HTTPException(status_code=400, detail=f"Failed to create test event: {e}")


@router.post("/trigger-rss-collection")
async def trigger_rss_collection():
    """Manually trigger RSS collection (for testing/debugging)."""
    try:
        from app.modules.ingestion.application.rss_collector import run_collector

        logger.info("[🔄] Triggering RSS collection...")
        run_collector()
        return {
            "status": "success",
            "message": "RSS collection triggered",
            "timestamp": datetime.utcnow().isoformat(),
        }
    except Exception as e:
        logger.error(f"[❌] RSS collection failed: {str(e)}")
        raise HTTPException(status_code=500, detail=f"RSS collection failed: {e}")


@router.post("/trigger-price-collection")
async def trigger_price_collection():
    """Manually trigger price collection (for testing/debugging)."""
    try:
        from app.modules.ingestion.application.price_collector import run_collector

        logger.info("[🔄] Triggering price collection...")
        run_collector()
        return {
            "status": "success",
            "message": "Price collection triggered",
            "timestamp": datetime.utcnow().isoformat(),
        }
    except Exception as e:
        logger.error(f"[❌] Price collection failed: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Price collection failed: {e}")


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
