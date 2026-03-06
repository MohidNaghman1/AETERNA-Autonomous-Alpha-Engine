"""
Ingestion module API router with enhanced filtering.
"""

from fastapi import APIRouter, Depends, HTTPException, status, Query, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import desc, and_, func
from app.shared.application.dependencies import get_db
from app.modules.ingestion.infrastructure.models import EventORM
from app.modules.ingestion.presentation.schemas import EventIn, EventOut
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

        rabbitmq_url = os.getenv("RABBITMQ_URL")
        host = os.getenv("RABBITMQ_HOST", "localhost")
        port = int(os.getenv("RABBITMQ_PORT", "5672"))
        user = os.getenv("RABBITMQ_USER", "guest")
        password = os.getenv("RABBITMQ_PASSWORD", "guest")
        vhost = os.getenv("RABBITMQ_VHOST", "/")

        # Try URL-based connection first
        if rabbitmq_url:
            conn_params = pika.URLParameters(rabbitmq_url)
            conn = pika.BlockingConnection([conn_params])
            diagnostics["rabbitmq"]["status"] = "✅ Connected (URL)"
            diagnostics["rabbitmq"]["host"] = "CloudAMQP"
        else:
            credentials = pika.PlainCredentials(user, password)
            conn = pika.BlockingConnection(
                pika.ConnectionParameters(
                    host=host, 
                    port=port,
                    virtual_host=vhost,
                    credentials=credentials, 
                    connection_attempts=1
                )
            )
            diagnostics["rabbitmq"]["status"] = "✅ Connected"
            diagnostics["rabbitmq"]["host"] = host
        
        conn.close()
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
async def trigger_rss_collection(background_tasks: BackgroundTasks):
    """Manually trigger RSS collection (for testing/debugging).
    
    Runs in background tasks queue without blocking the response.
    """
    try:
        from app.modules.ingestion.application.rss_collector import run_collector

        logger.info("[🔄] Queuing RSS collection...")
        background_tasks.add_task(run_collector)
        
        return {
            "status": "success",
            "message": "RSS collection queued",
            "timestamp": datetime.utcnow().isoformat(),
        }
    except Exception as e:
        logger.error(f"[❌] Failed to queue RSS collection: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to queue RSS collection: {e}")


@router.post("/trigger-price-collection")
async def trigger_price_collection(background_tasks: BackgroundTasks):
    """Manually trigger price collection (for testing/debugging).
    
    Runs in background tasks queue without blocking the response.
    """
    try:
        from app.modules.ingestion.application.price_collector import run_collector

        logger.info("[🔄] Queuing price collection...")
        background_tasks.add_task(run_collector)
        
        return {
            "status": "success",
            "message": "Price collection queued",
            "timestamp": datetime.utcnow().isoformat(),
        }
    except Exception as e:
        logger.error(f"[❌] Failed to queue price collection: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to queue price collection: {e}")


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


@router.get("/diagnostic/scheduler-status")
async def diagnostic_scheduler_status():
    """Check APScheduler status (for debugging)."""
    try:
        from app.main import background_scheduler
        
        if not background_scheduler:
            return {
                "status": "error",
                "message": "Scheduler not initialized",
                "scheduler_running": False,
                "jobs": None
            }
        
        jobs_info = []
        if background_scheduler.running:
            for job in background_scheduler.get_jobs():
                jobs_info.append({
                    "id": job.id,
                    "name": job.name,
                    "interval": str(job.trigger),
                    "next_run_time": str(job.next_run_time)
                })
        
        return {
            "status": "success",
            "scheduler_running": background_scheduler.running,
            "jobs_count": len(jobs_info),
            "jobs": jobs_info
        }
    except Exception as e:
        logger.error(f"[DIAGNOSTIC] Scheduler status check failed: {e}", exc_info=True)
        return {
            "status": "error",
            "error": str(e)
        }


@router.get("/diagnostic/test-rss-sync")
async def diagnostic_test_rss_sync():
    """Test RSS collection SYNCHRONOUSLY (for debugging). Blocks until complete."""
    try:
        from app.modules.ingestion.application.rss_collector import run_collector
        
        logger.info("[DIAGNOSTIC] Starting synchronous RSS collection...")
        run_collector()
        logger.info("[DIAGNOSTIC] RSS collection finished")
        
        return {
            "status": "success",
            "message": "RSS collection completed synchronously"
        }
    except Exception as e:
        logger.error(f"[DIAGNOSTIC] Sync RSS collection failed: {e}", exc_info=True)
        return {
            "status": "error",
            "error": str(e)
        }


@router.get("/diagnostic/test-consumer-poll")
async def diagnostic_test_consumer_poll():
    """Test consumer polling SYNCHRONOUSLY (for debugging). Processes up to 10 messages."""
    try:
        from app.modules.ingestion.application.consumer import run_consumer_poll
        
        logger.info("[DIAGNOSTIC] Starting synchronous consumer polling...")
        count = run_consumer_poll(batch_size=10)
        logger.info(f"[DIAGNOSTIC] Consumer polling finished, processed {count} messages")
        
        return {
            "status": "success",
            "message": f"Consumer polling completed, processed {count} messages",
            "processed_count": count
        }
    except Exception as e:
        logger.error(f"[DIAGNOSTIC] Sync consumer polling failed: {e}", exc_info=True)
        return {
            "status": "error",
            "error": str(e)
        }


@router.get("/diagnostic/rabbitmq-queue-depth")
async def diagnostic_rabbitmq_queue_depth():
    """Check RabbitMQ queue depth (diagnostic endpoint)."""
    import pika
    import os
    from dotenv import load_dotenv
    
    load_dotenv()
    
    RABBITMQ_URL = os.getenv("RABBITMQ_URL")
    RABBITMQ_HOST = os.getenv("RABBITMQ_HOST", "localhost")
    RABBITMQ_PORT = int(os.getenv("RABBITMQ_PORT", "5672"))
    RABBITMQ_QUEUE = os.getenv("RABBITMQ_QUEUE", "events")
    RABBITMQ_USER = os.getenv("RABBITMQ_USER", "guest")
    RABBITMQ_PASSWORD = os.getenv("RABBITMQ_PASSWORD", "guest")
    RABBITMQ_VHOST = os.getenv("RABBITMQ_VHOST", "/")
    
    try:
        # Connect to RabbitMQ
        if RABBITMQ_URL:
            try:
                conn_params = pika.URLParameters(RABBITMQ_URL)
                connection = pika.BlockingConnection([conn_params])
            except Exception as e:
                credentials = pika.PlainCredentials(RABBITMQ_USER, RABBITMQ_PASSWORD)
                connection = pika.BlockingConnection(
                    pika.ConnectionParameters(
                        host=RABBITMQ_HOST,
                        port=RABBITMQ_PORT,
                        virtual_host=RABBITMQ_VHOST,
                        credentials=credentials,
                    )
                )
        else:
            credentials = pika.PlainCredentials(RABBITMQ_USER, RABBITMQ_PASSWORD)
            connection = pika.BlockingConnection(
                pika.ConnectionParameters(
                    host=RABBITMQ_HOST,
                    port=RABBITMQ_PORT,
                    virtual_host=RABBITMQ_VHOST,
                    credentials=credentials,
                )
            )
        
        channel = connection.channel()
        channel.queue_declare(queue=RABBITMQ_QUEUE, durable=True)
        
        # Get queue info using passive declaration
        method = channel.queue_declare(queue=RABBITMQ_QUEUE, passive=True)
        message_count = method.method.message_count
        consumer_count = method.method.consumer_count
        
        connection.close()
        
        return {
            "status": "success",
            "queue_name": RABBITMQ_QUEUE,
            "message_count": message_count,
            "consumer_count": consumer_count,
            "rabbitmq_url_set": bool(RABBITMQ_URL),
        }
    except Exception as e:
        logger.error(f"[DIAGNOSTIC] RabbitMQ queue depth check failed: {e}")
        return {
            "status": "error",
            "error": str(e),
            "queue_name": RABBITMQ_QUEUE,
        }
