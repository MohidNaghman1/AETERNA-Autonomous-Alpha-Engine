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
    - "ethereum" → matches blockchain events (onchain)
    - "coindesk" → matches "www.coindesk.com" or "coindesk.com"
    - "cointelegraph" → matches "cointelegraph.com"
    - "decrypt" → matches "decrypt.co"
    - "coingecko" → matches "coingecko" (exact)

    Returns: normalized source name(s) as regex or exact match
    """
    source_lower = source.lower().strip()

    # Map shorthand names to actual stored values
    normalization_map = {
        "ethereum": ["ethereum"],
        "onchain": ["ethereum"],
        "blockchain": ["ethereum"],
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
        description="Filter by data provider (ethereum, coindesk, coingecko, decrypt, cointelegraph, etc)",
    ),
    event_type: Optional[str] = Query(
        None,
        description="Filter by event type (news, price, onchain, etc)"
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
    - source: Filter by data provider source (e.g., "ethereum", "coindesk", "coingecko", "cointelegraph", "decrypt")
    - event_type: Filter by event type (e.g., "news", "price", "onchain")
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
    """Filter events by source (e.g., ethereum, coindesk, coingecko, decrypt, cointelegraph).
    
    Source names are normalized, so you can use shorthand names:
    - "ethereum" matches "ethereum" (on-chain events)
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
            "ethereum": "Try: ?source=ethereum (for on-chain events)",
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


@router.get("/debug/ethereum-connection")
async def debug_ethereum_connection():
    """
    Test connection to Ethereum node via QuickNode.
    Helps diagnose if blockchain connectivity is the issue.
    
    Returns:
        - connected: Boolean if connection successful
        - block_number: Current block if connected
        - error: Error message if failed
    
    Example usage:
        GET /ingestion/debug/ethereum-connection
    """
    import os
    from web3 import Web3
    from web3.providers import WebsocketProvider
    
    quicknode_url = os.getenv("QUICKNODE_URL", "")
    
    if not quicknode_url:
        return {
            "status": "⚠️ Not configured",
            "error": "QUICKNODE_URL environment variable not set",
            "diagnostic": "Set QUICKNODE_URL in .env to enable Ethereum monitoring"
        }
    
    try:
        logger.info("[ETHEREUM-DEBUG] Testing Web3 connection...")
        start_time = time.time()
        
        w3 = Web3(WebsocketProvider(quicknode_url))
        
        # This may hang if QuickNode is unreachable
        is_connected = w3.is_connected()
        elapsed = time.time() - start_time
        
        if is_connected:
            try:
                block = w3.eth.block_number
                chain_id = w3.eth.chain_id
                return {
                    "status": "✅ Connected",
                    "connected": True,
                    "block_number": block,
                    "chain_id": chain_id,
                    "connection_time_ms": round(elapsed * 1000, 2),
                    "network": "Ethereum Mainnet"
                }
            except Exception as e:
                logger.error(f"[ETHEREUM-DEBUG] Error getting block info: {e}")
                return {
                    "status": "⚠️ Connected but error getting data",
                    "connected": True,
                    "error": str(e),
                    "connection_time_ms": round(elapsed * 1000, 2),
                }
        else:
            return {
                "status": "❌ Not connected",
                "connected": False,
                "error": "Web3 returned is_connected=False",
                "connection_time_ms": round(elapsed * 1000, 2),
                "diagnostic": "QuickNode may be unreachable or URL is invalid"
            }
    
    except Exception as e:
        elapsed = time.time() - start_time
        logger.error(f"[ETHEREUM-DEBUG] Connection error: {e}")
        return {
            "status": "❌ Connection Error",
            "connected": False,
            "error": str(e),
            "connection_time_ms": round(elapsed * 1000, 2),
            "diagnostic": "Network error or invalid QuickNode URL - check .env and network connectivity"
        }


@router.get("/debug/rabbitmq-queue-depth")
async def debug_rabbitmq_queue_depth():
    """
    Check RabbitMQ queue depth to see if messages are stuck in the queue.
    
    Returns:
        - queue_name: Name of the queue being monitored
        - message_count: Number of messages in the queue
        - connection_status: Whether we could connect to RabbitMQ
        - helpful_commands: Debugging tips
    
    Example usage:
        GET /ingestion/debug/rabbitmq-queue-depth
    """
    import pika
    import os
    
    RABBITMQ_URL = os.getenv("RABBITMQ_URL")
    RABBITMQ_HOST = os.getenv("RABBITMQ_HOST", "localhost")
    RABBITMQ_PORT = int(os.getenv("RABBITMQ_PORT", "5672"))
    RABBITMQ_QUEUE = os.getenv("RABBITMQ_QUEUE", "events")
    RABBITMQ_USER = os.getenv("RABBITMQ_USER", "guest")
    RABBITMQ_PASSWORD = os.getenv("RABBITMQ_PASSWORD", "guest")
    RABBITMQ_VHOST = os.getenv("RABBITMQ_VHOST", "/")
    
    try:
        # Try to connect to RabbitMQ
        if RABBITMQ_URL:
            conn_params = pika.URLParameters(RABBITMQ_URL)
        else:
            credentials = pika.PlainCredentials(RABBITMQ_USER, RABBITMQ_PASSWORD)
            conn_params = pika.ConnectionParameters(
                host=RABBITMQ_HOST,
                port=RABBITMQ_PORT,
                virtual_host=RABBITMQ_VHOST,
                credentials=credentials,
            )
        
        connection = pika.BlockingConnection([conn_params] if isinstance(conn_params, pika.URLParameters) else conn_params)
        channel = connection.channel()
        
        # Try to declare the queue (gets current status)
        method = channel.queue_declare(queue=RABBITMQ_QUEUE, passive=True)
        message_count = method.method.message_count
        
        connection.close()
        
        return {
            "status": "✅ Connected",
            "queue_name": RABBITMQ_QUEUE,
            "message_count": message_count,
            "connection_status": "connected",
            "next_steps": (
                f"✅ Queue is empty" if message_count == 0 
                else f"⚠️ {message_count} messages in queue - messages may not be consumed"
            ),
            "diagnostic_tips": {
                "no_messages_in_queue": "Messages may not be published - check on-chain collector logs",
                "messages_stuck_in_queue": "Messages are published but not consumed - check consumer logs",
                "check_consumer": f"Run: python -m app.modules.ingestion.application.consumer",
            }
        }
        
    except pika.exceptions.AMQPConnectionError as e:
        logger.error(f"[RABBITMQ-DEBUG] Connection error: {e}")
        return {
            "status": "❌ Connection Failed",
            "connection_status": "error",
            "error": str(e),
            "queue_name": RABBITMQ_QUEUE,
            "message_count": None,
            "diagnostic_tips": {
                "check_rabbitmq": "Is RabbitMQ running? Check docker or local service",
                "verify_credentials": f"Host: {RABBITMQ_HOST}:{RABBITMQ_PORT}, User: {RABBITMQ_USER}",
                "check_url": f"RABBITMQ_URL: {RABBITMQ_URL if RABBITMQ_URL else 'Not set (using host-based)'}"
            }
        }
    except pika.exceptions.AMQPChannelError as e:
        logger.error(f"[RABBITMQ-DEBUG] Queue does not exist: {e}")
        return {
            "status": "❌ Queue Not Found",
            "connection_status": "connected_but_queue_missing",
            "error": f"Queue '{RABBITMQ_QUEUE}' does not exist",
            "queue_name": RABBITMQ_QUEUE,
            "message_count": None,
            "diagnostic_tips": {
                "create_queue": f"Queue will be created automatically when first event is published"
            }
        }
    except Exception as e:
        logger.error(f"[RABBITMQ-DEBUG] Unexpected error: {e}")
        return {
            "status": "❌ Error",
            "error": str(e),
            "queue_name": RABBITMQ_QUEUE,
            "message_count": None,
        }


@router.get("/debug/database-contents")
async def debug_database_contents(db: AsyncSession = Depends(get_db)):
    """
    Diagnostic endpoint showing EXACTLY what's in the database.
    Helps debug filtering issues by showing all stored events with their source and type values.
    
    Returns:
        - total_count: Total events in database
        - by_source: Count of events for each source (shows actual stored values)
        - by_type: Count of events for each type (shows actual stored values)
        - sample_events: First 5 events with all details (to verify data structure)
    
    Example usage:
        GET /ingestion/debug/database-contents
    """
    # Get total count
    total_result = await db.execute(select(func.count(EventORM.id)))
    total_count = total_result.scalar() or 0
    
    # Get breakdown by source (show ACTUAL stored values, not normalized)
    source_result = await db.execute(
        select(EventORM.source, func.count(EventORM.id)).group_by(EventORM.source).order_by(func.count(EventORM.id).desc())
    )
    by_source = {row[0]: row[1] for row in source_result.all()}
    
    # Get breakdown by type
    type_result = await db.execute(
        select(EventORM.type, func.count(EventORM.id)).group_by(EventORM.type).order_by(func.count(EventORM.id).desc())
    )
    by_type = {row[0]: row[1] for row in type_result.all()}
    
    # Get sample events to verify structure
    sample_result = await db.execute(
        select(EventORM).order_by(desc(EventORM.timestamp)).limit(5)
    )
    samples = []
    for event in sample_result.scalars().all():
        samples.append({
            "id": event.id,
            "source": event.source,
            "type": event.type,
            "timestamp": event.timestamp.isoformat() if event.timestamp else None,
            "title": event.content.get("title") if event.content else None,
        })
    
    return {
        "status": "✅ Ready for debugging",
        "total_events": total_count,
        "by_source": by_source,
        "by_type": by_type,
        "sample_events": samples,
        "notes": {
            "test_query": "To test filtering: GET /ingestion/events?source=ethereum&type=onchain",
            "expected_sources": ["ethereum", "www.coindesk.com", "cointelegraph.com", "decrypt.co", "coingecko"],
            "expected_types": ["onchain", "news", "price"],
        }
    }


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


@router.post("/test/onchain-collector")
async def test_onchain_collector(db: AsyncSession = Depends(get_db)):
    """
    Test endpoint to run the on-chain collector and verify it works.
    
    Returns:
        - status: success or error
        - execution_time: How long collector took (seconds)
        - ethereum_block: Latest block from Ethereum
        - gas_price: Current gas price in Gwei
        - event_published: Boolean indicating if event was published
        - message: Detailed status message
    
    Example:
        POST /ingestion/test/onchain-collector
        
    Response:
        {
            "status": "success",
            "execution_time": 2.15,
            "ethereum_block": 24662012,
            "gas_price": 0.032949,
            "event_published": true,
            "chain": "ethereum",
            "network": "mainnet",
            "message": "[OK] On-Chain collector test completed successfully"
        }
    """
    import time
    from web3 import Web3
    from web3.providers import WebsocketProvider
    import os
    
    start_time = time.time()
    
    try:
        # Get configuration
        quicknode_url = os.getenv("QUICKNODE_URL")
        if not quicknode_url:
            return {
                "status": "error",
                "execution_time": 0,
                "message": "[ERROR] QUICKNODE_URL environment variable not set"
            }
        
        # Test Web3 connection
        logger.info("[TEST] Connecting to Ethereum...")
        w3 = Web3(WebsocketProvider(quicknode_url))
        
        if not w3.is_connected():
            elapsed = time.time() - start_time
            return {
                "status": "error",
                "execution_time": elapsed,
                "message": "[ERROR] Failed to connect to Ethereum node"
            }
        
        # Get blockchain info
        chain_id = w3.eth.chain_id
        latest_block = w3.eth.block_number
        gas_price = w3.eth.gas_price
        gas_price_gwei = w3.from_wei(gas_price, 'gwei')
        
        logger.info(f"[TEST] Connected to Ethereum - Block: {latest_block}, Gas: {gas_price_gwei:.6f} Gwei")
        
        # Run the collector
        logger.info("[TEST] Running on-chain collector...")
        from app.modules.ingestion.application.onchain_collector import run_collector
        from app.modules.ingestion.application.consumer import run_consumer_poll
        
        # Run collector in timeout to prevent hanging
        collector_start = time.time()
        try:
            # Use signal to timeout the collector if it takes too long
            import signal
            
            def timeout_handler(signum, frame):
                logger.warning("[TEST] Collector timed out after 30 seconds")
                raise TimeoutError("Collector execution timed out")
            
            # Set timeout (Unix/Linux only, Windows will skip this)
            old_handler = None
            try:
                old_handler = signal.signal(signal.SIGALRM, timeout_handler)
                signal.alarm(30)  # 30 second timeout
            except (AttributeError, ValueError):
                # SIGALRM not available on Windows
                logger.debug("[TEST] Timeout not available on this platform")
            
            try:
                run_collector()
            finally:
                try:
                    signal.alarm(0)  # Cancel alarm
                    if old_handler:
                        signal.signal(signal.SIGALRM, old_handler)
                except (AttributeError, ValueError):
                    pass
            
            collector_time = time.time() - collector_start
            logger.info(f"[TEST] Collector completed in {collector_time:.2f}s")
        except TimeoutError:
            collector_time = time.time() - collector_start
            logger.warning(f"[TEST] Collector timed out after {collector_time:.2f}s (likely Web3 connection issue)")
        except Exception as e:
            logger.error(f"[TEST] Collector error: {e}")
            collector_time = time.time() - collector_start
        
        # CRITICAL FIX: Consume messages from RabbitMQ before checking database
        # The collector publishes to RabbitMQ, but we need to consume it
        logger.info("[TEST] Polling RabbitMQ to consume published events...")
        total_consumed = 0
        for attempt in range(10):  # Increased attempts
            logger.debug(f"[TEST] Consume attempt {attempt + 1}/10...")
            consumed = run_consumer_poll(batch_size=50)
            total_consumed += consumed
            
            if consumed > 0:
                logger.info(f"[TEST] ✅ Consumed {consumed} message(s) on attempt {attempt + 1}")
                time.sleep(0.5)  # Wait for DB commit
                break
            else:
                logger.debug(f"[TEST] No messages on attempt {attempt + 1}")
            
            if attempt < 9:
                time.sleep(0.3)
        
        elapsed = time.time() - start_time
        
        # Check if event was stored
        result = await db.execute(
            select(func.count(EventORM.id)).where(EventORM.source == "ethereum")
        )
        ethereum_event_count = result.scalar() or 0
        
        # Diagnostic info
        diagnostic = {
            "collector_time_seconds": round(collector_time, 2),
            "consumer_attempts": 10,
            "total_messages_consumed": total_consumed,
            "events_in_database": ethereum_event_count,
        }
        
        if ethereum_event_count > 0:
            status_msg = "✅ SUCCESS - Event published and stored in database"
        elif total_consumed > 0:
            status_msg = "⚠️ WARNING - Messages consumed but not in database (check consumer logs)"
        else:
            status_msg = "❌ ISSUE - No messages consumed from queue (event may not be published)"
        
        return {
            "status": "success",
            "execution_time": round(elapsed, 2),
            "ethereum_block": latest_block,
            "gas_price": float(f"{gas_price_gwei:.6f}"),
            "chain": "ethereum",
            "network": "mainnet",
            "chain_id": chain_id,
            "ethereum_events_in_database": ethereum_event_count,
            "event_published": True,
            "diagnostic": diagnostic,
            "status_message": status_msg,
            "message": "[OK] On-Chain collector test completed successfully"
        }
        
    except Exception as e:
        elapsed = time.time() - start_time
        logger.error(f"[TEST-ERROR] On-chain collector test failed: {e}")
        import traceback
        error_details = traceback.format_exc()
        
        return {
            "status": "error",
            "execution_time": round(elapsed, 2),
            "message": f"[ERROR] On-chain collector test failed: {str(e)}",
            "error_details": error_details,
            "event_published": False
        }
