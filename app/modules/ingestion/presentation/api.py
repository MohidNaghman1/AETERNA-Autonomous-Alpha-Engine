"""
Ingestion module API router with enhanced filtering.
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import desc, and_, func, or_
from app.shared.application.dependencies import get_db
from app.modules.ingestion.infrastructure.models import EventORM
from app.modules.ingestion.presentation.schemas import EventOut
from typing import List, Optional
from datetime import datetime
import logging
import time
import os
import pika

router = APIRouter()
logger = logging.getLogger(__name__)


def normalize_source(source: str) -> List[str]:
    """
    Normalize source names for flexible querying.
    Maps user-friendly names to actual database values.

    Blockchain sources:
    - "ethereum_blockchain" or "ethereum" → matches blockchain events (stored as "ethereum")

    News sources:
    - "coindesk" → matches "www.coindesk.com" or "coindesk.com"
    - "cointelegraph" → matches "cointelegraph.com"
    - "decrypt" → matches "decrypt.co"

    Price sources:
    - "coingecko" → matches "coingecko" (exact)

    Returns: list of possible source names to match in database
    """
    source_lower = source.lower().strip()

    # Map user-friendly names to actual stored values in database
    normalization_map = {
        # Blockchain sources (user-friendly name → database value)
        "ethereum_blockchain": ["ethereum"],
        "ethereum": ["ethereum"],  # Keep backward compatibility
        "onchain": ["ethereum"],
        "blockchain": ["ethereum"],
        # News sources
        "coindesk": ["www.coindesk.com", "coindesk.com", "coindesk"],
        "cointelegraph": ["cointelegraph.com", "cointelegraph"],
        "decrypt": ["decrypt.co", "decrypt"],
        # Price sources
        "coingecko": ["coingecko"],
        # Exact source names (fallback)
        "www.coindesk.com": ["www.coindesk.com"],
        "coindesk.com": ["coindesk.com"],
        "cointelegraph.com": ["cointelegraph.com"],
        "decrypt.co": ["decrypt.co"],
    }

    return normalization_map.get(source_lower, [source])


def normalize_type(event_type: str) -> List[str]:
    """
    Normalize event type names for flexible querying.
    Maps user-friendly names to actual database values.

    Blockchain types:
    - "token_transfer" or "onchain" → matches blockchain events (stored as "onchain")

    News types:
    - "news" → matches news articles (stored as "news")

    Price types:
    - "price" → matches price data (stored as "price")

    Returns: list of possible type names to match in database
    """
    type_lower = event_type.lower().strip()

    # Map user-friendly names to actual stored values in database
    normalization_map = {
        # Blockchain types (user-friendly name → database value)
        "token_transfer": ["onchain"],
        "onchain": ["onchain"],  # Keep backward compatibility
        "blockchain": ["onchain"],
        "erc20_transfer": ["onchain"],
        # News types
        "news": ["news"],
        # Price types
        "price": ["price"],
    }

    return normalization_map.get(type_lower, [event_type])


# Example endpoint (health check for ingestion)
@router.get("/health")
def ingestion_health():
    return {"status": "ok"}


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
        description="Filter by data source (ethereum_blockchain, coindesk, coingecko, decrypt, cointelegraph, etc)",
    ),
    event_type: Optional[str] = Query(
        None,
        alias="type",
        description="Filter by event type (news, price, onchain, etc)",
    ),
    start_date: Optional[datetime] = Query(
        None, description="Filter events after this date (ISO format)"
    ),
    end_date: Optional[datetime] = Query(
        None, description="Filter events before this date (ISO format)"
    ),
    db: AsyncSession = Depends(get_db),
):
    """
    Get events with flexible filtering support.

    Supports filtering by source, type, and date range.
    All filters are optional and can be combined.

    Query Parameters:
    - skip: Pagination offset (default: 0)
    - limit: Number of results to return (default: 100, max: 500)
    - source: Filter by source - use shorthand (ethereum, coindesk, decrypt, cointelegraph, coingecko) or full name
    - type: Filter by event type (news, price, onchain)
    - start_date: Get events after this date (ISO format, e.g., 2026-03-16T10:00:00)
    - end_date: Get events before this date (ISO format)

    Examples:
    - GET /ingestion/events?source=ethereum_blockchain&limit=10 - Get blockchain token transfers
    - GET /ingestion/events?source=decrypt&type=news&limit=5 - Get Decrypt news
    - GET /ingestion/events?type=price&limit=50 - Get all price events
    - GET /ingestion/events?skip=100&limit=50 - Paginate results
    - GET /ingestion/events?source=coindesk&start_date=2026-03-15T00:00:00 - CoinDesk after date

    Returns:
        List of events matching all filters, ordered by timestamp (newest first)
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
        # Normalize type and create OR filter for all possible variations
        possible_types = normalize_type(event_type)
        logger.info(f"[DEBUG] Filtering by type: {event_type} → {possible_types}")
        type_filter = or_(*[EventORM.type == t for t in possible_types])
        filters.append(type_filter)
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


@router.get("/sources")
async def get_available_sources(db: AsyncSession = Depends(get_db)):
    """
    Get all available data sources with event counts.

    Returns all sources currently in the database with statistics.
    Use these source names in filters: ?source=coindesk, ?source=ethereum, etc.

    Example response:
        {
            "sources": {
                "www.coindesk.com": 2143,
                "cointelegraph.com": 2506,
                "decrypt.co": 3091,
                "coingecko": 1628,
                "ethereum": 11
            },
            "total_unique_sources": 5,
            "total_events": 9379,
            "filter_usage": {
                "ethereum": "Try: ?source=ethereum (for on-chain events)",
                "coindesk": "Try: ?source=coindesk (matches www.coindesk.com)",
                ...
            }
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
            "ethereum_blockchain": "Try: ?source=ethereum_blockchain (for on-chain blockchain transfers)",
            "ethereum": "Try: ?source=ethereum (backward compatible alias)",
            "coindesk": "Try: ?source=coindesk (matches www.coindesk.com news)",
            "cointelegraph": "Try: ?source=cointelegraph (matches cointelegraph.com news)",
            "decrypt": "Try: ?source=decrypt (matches decrypt.co news)",
            "coingecko": "Try: ?source=coingecko (price data)",
        },
    }


@router.get("/stats")
async def get_ingestion_stats(db: AsyncSession = Depends(get_db)):
    """
    Get comprehensive statistics about ingested events.

    Returns:
        - total_events: Total number of events in database
        - by_source: Count grouped by data source
        - by_type: Count grouped by event type (news, price, onchain)
        - last_updated: Timestamp of most recent event

    Example response:
        {
            "total_events": 9379,
            "by_source": {
                "decrypt.co": 3091,
                "cointelegraph.com": 2506,
                "www.coindesk.com": 2143,
                "coingecko": 1628,
                "ethereum": 11
            },
            "by_type": {
                "news": 6840,
                "price": 1460,
                "onchain": 11
            },
            "last_updated": "2026-03-16T14:25:07"
        }
    """
    # Count total events
    total_result = await db.execute(select(func.count(EventORM.id)))
    total = total_result.scalar() or 0

    # Count by source
    source_result = await db.execute(
        select(EventORM.source, func.count(EventORM.id))
        .group_by(EventORM.source)
        .order_by(func.count(EventORM.id).desc())
    )
    sources = {row[0]: row[1] for row in source_result.all()}

    # Count by type
    type_result = await db.execute(
        select(EventORM.type, func.count(EventORM.id))
        .group_by(EventORM.type)
        .order_by(func.count(EventORM.id).desc())
    )
    types = {row[0]: row[1] for row in type_result.all()}

    # Get last updated timestamp
    latest_result = await db.execute(
        select(EventORM.timestamp).order_by(desc(EventORM.timestamp)).limit(1)
    )
    latest_timestamp = latest_result.scalar()
    last_updated = latest_timestamp.isoformat() if latest_timestamp else None

    return {
        "total_events": total,
        "by_source": sources,
        "by_type": types,
        "last_updated": last_updated,
    }


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
            "diagnostic": "Set QUICKNODE_URL in .env to enable Ethereum monitoring",
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
                    "network": "Ethereum Mainnet",
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
                "diagnostic": "QuickNode may be unreachable or URL is invalid",
            }

    except Exception as e:
        elapsed = time.time() - start_time
        logger.error(f"[ETHEREUM-DEBUG] Connection error: {e}")
        return {
            "status": "❌ Connection Error",
            "connected": False,
            "error": str(e),
            "connection_time_ms": round(elapsed * 1000, 2),
            "diagnostic": "Network error or invalid QuickNode URL - check .env and network connectivity",
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

        connection = pika.BlockingConnection(
            [conn_params]
            if isinstance(conn_params, pika.URLParameters)
            else conn_params
        )
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
                "✅ Queue is empty"
                if message_count == 0
                else f"⚠️ {message_count} messages in queue - messages may not be consumed"
            ),
            "diagnostic_tips": {
                "no_messages_in_queue": "Messages may not be published - check on-chain collector logs",
                "messages_stuck_in_queue": "Messages are published but not consumed - check consumer logs",
                "check_consumer": "Run: python -m app.modules.ingestion.application.consumer",
            },
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
                "check_url": f"RABBITMQ_URL: {RABBITMQ_URL if RABBITMQ_URL else 'Not set (using host-based)'}",
            },
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
                "create_queue": "Queue will be created automatically when first event is published"
            },
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
        select(EventORM.source, func.count(EventORM.id))
        .group_by(EventORM.source)
        .order_by(func.count(EventORM.id).desc())
    )
    by_source = {row[0]: row[1] for row in source_result.all()}

    # Get breakdown by type
    type_result = await db.execute(
        select(EventORM.type, func.count(EventORM.id))
        .group_by(EventORM.type)
        .order_by(func.count(EventORM.id).desc())
    )
    by_type = {row[0]: row[1] for row in type_result.all()}

    # Get sample events to verify structure
    sample_result = await db.execute(
        select(EventORM).order_by(desc(EventORM.timestamp)).limit(5)
    )
    samples = []
    for event in sample_result.scalars().all():
        samples.append(
            {
                "id": event.id,
                "source": event.source,
                "type": event.type,
                "timestamp": event.timestamp.isoformat() if event.timestamp else None,
                "title": event.content.get("title") if event.content else None,
            }
        )

    return {
        "status": "✅ Ready for debugging",
        "total_events": total_count,
        "by_source": by_source,
        "by_type": by_type,
        "sample_events": samples,
        "notes": {
            "test_query": "To test filtering: GET /ingestion/events?source=ethereum_blockchain (for blockchain events)",
            "filter_names": {
                "ethereum": "in database as 'ethereum', filter with ?source=ethereum_blockchain or ?source=ethereum",
                "onchain": "in database as 'onchain', represents blockchain token transfers",
                "news": "news articles from various feeds",
                "price": "price data from CoinGecko",
            },
            "expected_sources": [
                "ethereum",
                "www.coindesk.com",
                "cointelegraph.com",
                "decrypt.co",
                "coingecko",
            ],
            "expected_types": ["onchain", "news", "price"],
        },
    }
