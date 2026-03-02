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

router = APIRouter()


# Example endpoint (health check for ingestion)
@router.get("/health")
def ingestion_health():
    return {"status": "ok"}


@router.post("/events", response_model=EventOut, status_code=201)
async def create_event(event: EventIn, db: AsyncSession = Depends(get_db)):
    db_event = EventORM(**event.dict())
    db.add(db_event)
    try:
        await db.commit()
        await db.refresh(db_event)
    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=400, detail=f"Failed to store event: {e}")
    return db_event


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
