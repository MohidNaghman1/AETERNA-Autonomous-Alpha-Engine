"""
Ingestion module API router with enhanced filtering.
"""

from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import desc, and_, func, or_
from app.shared.application.dependencies import get_db
from app.modules.ingestion.infrastructure.models import EventORM
from app.modules.ingestion.presentation.schemas import EventIn, EventOut
from typing import List, Optional
from datetime import datetime
import logging

router = APIRouter()
logger = logging.getLogger(__name__)


def normalize_source(source: str) -> List[str]:
    """
    Normalize source names for flexible querying.
    Handles common variations:
    - "coindesk" → matches "www.coindesk.com" or "coindesk.com"
    - "cointelegraph" → matches "cointelegraph.com"
    - "decrypt" → matches "decrypt.co"
    - "coingecko" → matches "coingecko" (exact)

    Returns: normalized source name(s) as regex or exact match
    """
    source_lower = source.lower().strip()

    # Map shorthand names to actual stored values
    normalization_map = {
        "coindesk": ["www.coindesk.com", "coindesk.com", "coindesk"],
        "cointelegraph": ["cointelegraph.com", "cointelegraph"],
        "decrypt": ["decrypt.co", "decrypt"],
        "coingecko": ["coingecko"],
        "www.coindesk.com": ["www.coindesk.com"],
        "coindesk.com": ["coindesk.com"],
        "cointelegraph.com": ["cointelegraph.com"],
        "decrypt.co": ["decrypt.co"],
    }

    return normalization_map.get(source_lower, [source])


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
    source: Optional[str] = Query(
        None,
        description="Filter by data provider (coindesk, coingecko, decrypt, cointelegraph, etc)",
    ),
    event_type: Optional[str] = Query(
        None,
        description="Filter by event type (news, price, etc)"
    ),
    start_date: Optional[datetime] = Query(
        None,
        description="Filter events after this date (ISO format)"
    ),
    end_date: Optional[datetime] = Query(
        None,
        description="Filter events before this date (ISO format)"
    ),
    db: AsyncSession = Depends(get_db),
):
    """
    List events with optional filtering.

    Query Parameters:
    - skip: Offset for pagination (default: 0)
    - limit: Number of events to return (default: 100, max: 500)
    - source: Filter by data provider source (e.g., "coindesk", "coingecko", "cointelegraph", "decrypt")
    - event_type: Filter by event type (e.g., "news", "price")
    - start_date: Filter events after this date (ISO format)
    - end_date: Filter events before this date (ISO format)

    Returns:
        List of events matching all provided filters
    """
    query = select(EventORM)

    # Apply filters
    filters = []
    if source:
        # Normalize source and create OR filter for all possible variations
        possible_sources = normalize_source(source)
        logger.info(f"[DEBUG] Filtering by source: {source} → {possible_sources}")
        source_filter = or_(*[EventORM.source == s for s in possible_sources])
        filters.append(source_filter)
    if event_type:
        logger.info(f"[DEBUG] Filtering by event_type: {event_type}")
        filters.append(EventORM.type == event_type)
    if start_date:
        logger.info(f"[DEBUG] Filtering by start_date: {start_date}")
        filters.append(EventORM.timestamp >= start_date)
    if end_date:
        logger.info(f"[DEBUG] Filtering by end_date: {end_date}")
        filters.append(EventORM.timestamp <= end_date)

    if filters:
        query = query.where(and_(*filters))

    # Order by timestamp descending, apply pagination
    result = await db.execute(
        query.order_by(desc(EventORM.timestamp)).offset(skip).limit(limit)
    )
    events = result.scalars().all()
    logger.info(
        f"[✓] Retrieved {len(events)} events with filters: source={source}, type={event_type}"
    )
    return events


@router.get("/search/by-source/{source}", response_model=List[EventOut])
async def list_events_by_source(
    source: str,
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    db: AsyncSession = Depends(get_db),
):
    """Filter events by source (e.g., coindesk, coingecko, decrypt, cointelegraph).
    
    Source names are normalized, so you can use shorthand names:
    - "coindesk" matches "www.coindesk.com" or "coindesk.com"
    - "cointelegraph" matches "cointelegraph.com"
    - "decrypt" matches "decrypt.co"
    - "coingecko" matches "coingecko"
    """
    # Normalize source and create OR filter for all possible variations
    possible_sources = normalize_source(source)
    logger.info(f"[DEBUG] Querying by source: {source} → {possible_sources}")
    
    source_filter = or_(*[EventORM.source == s for s in possible_sources])
    result = await db.execute(
        select(EventORM)
        .where(source_filter)
        .order_by(desc(EventORM.timestamp))
        .offset(skip)
        .limit(limit)
    )
    events = result.scalars().all()
    logger.info(f"[✓] Retrieved {len(events)} events from source: {source}")
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
    logger.info(f"Retrieved {len(events)} events of type: {event_type}")
    return events


@router.get("/sources")
async def get_available_sources(db: AsyncSession = Depends(get_db)):
    """
    Get all available data sources with event counts.
    
    Returns:
        List of sources and number of events from each source
        
    Example response:
        {
            "sources": {
                "www.coindesk.com": 42,
                "cointelegraph.com": 85,
                "decrypt.co": 67,
                "coingecko": 234
            },
            "total_unique_sources": 4,
            "total_events": 428
        }
    """
    # Get all unique sources with event counts
    source_result = await db.execute(
        select(EventORM.source, func.count(EventORM.id))
        .group_by(EventORM.source)
        .order_by(func.count(EventORM.id).desc())
    )
    sources = {row[0]: row[1] for row in source_result.all()}
    
    # Get total events count
    total_result = await db.execute(select(func.count(EventORM.id)))
    total = total_result.scalar() or 0
    
    logger.info(f"[✓] Available sources: {list(sources.keys())}")
    
    return {
        "sources": sources,
        "total_unique_sources": len(sources),
        "total_events": total,
        "filter_usage": {
            "coindesk": "Try: ?source=coindesk (matches www.coindesk.com)",
            "cointelegraph": "Try: ?source=cointelegraph",
            "decrypt": "Try: ?source=decrypt",
            "coingecko": "Try: ?source=coingecko"
        }
    }


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
