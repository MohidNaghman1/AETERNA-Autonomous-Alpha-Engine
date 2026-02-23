"""
Ingestion module API router (placeholder for future endpoints).
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from app.shared.application.dependencies import get_db
from app.modules.ingestion.infrastructure.models import EventORM
from .schemas import EventIn, EventOut
from typing import List

router = APIRouter()

# Example endpoint (health check for ingestion)
@router.get("/ingestion/health")
def ingestion_health():
    return {"status": "ok"}

@router.post("/ingestion/events", response_model=EventOut, status_code=201)
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

@router.get("/ingestion/events/{event_id}", response_model=EventOut)
async def get_event(event_id: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(EventORM).where(EventORM.id == event_id))
    event = result.scalar_one_or_none()
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")
    return event

@router.get("/ingestion/events", response_model=List[EventOut])
async def list_events(skip: int = 0, limit: int = 100, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(EventORM).offset(skip).limit(limit))
    events = result.scalars().all()
    return events
