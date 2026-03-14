"""Alert API endpoints for listing, retrieving, marking as read, and dismissing alerts.

Provides REST endpoints for users to access their alert history with filtering and pagination.
All endpoints require authentication and enforce user ownership of alerts.
"""

from fastapi import APIRouter, HTTPException, Query, Depends, status
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, desc, or_
from app.shared.application.dependencies import get_db, get_current_user
from app.modules.admin.application.dependencies import require_role
from app.modules.alerting.infrastructure.models import Alert as AlertORM
from app.modules.alerting.presentation.schema import Alert, AlertDismissResponse
from app.modules.ingestion.infrastructure.models import EventORM
from datetime import datetime
from typing import List, Optional
import csv
from io import StringIO
import logging

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/alerts", tags=["alerts"])


async def get_alerts_query(
    db: AsyncSession,
    user_id: int,
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    priority: Optional[str] = None,
    entity: Optional[str] = None,
    source: Optional[str] = None,
    channels: Optional[str] = None,
    skip: int = 0,
    limit: int = 50,
):
    """
    Build and execute alert query with filters.

    Args:
        db: Database session
        user_id: Filter by user ID
        start_date: Filter events after this date
        end_date: Filter events before this date
        priority: Filter by priority (HIGH, MEDIUM, LOW)
        entity: Filter by entity/token (from event mentions)
        source: Filter by data provider/feed source (e.g., 'coindesk', 'coingecko', 'cointelegraph')
        channels: Filter by alert delivery channel (e.g., 'email', 'telegram', 'sms')
        skip: Offset for pagination
        limit: Number of results (max 100)

    Returns:
        List of Alert ORM objects with related events
    """
    # Get both user's personal alerts AND system broadcast alerts (user_id=None or user_id=0)
    query = select(AlertORM).where(
        (AlertORM.user_id == user_id)
        | (AlertORM.user_id == 0)
        | (AlertORM.user_id.is_(None))
    )

    # Apply filters
    filters = []
    if start_date:
        filters.append(AlertORM.created_at >= start_date)
    if end_date:
        filters.append(AlertORM.created_at <= end_date)
    if priority:
        filters.append(AlertORM.priority == priority)

    # Track if we've joined EventORM to avoid duplicate joins
    event_joined = False

    # Filter by entity - requires joining with events and checking mentions in content
    if entity:
        query = query.join(EventORM, AlertORM.event_id == EventORM.id, isouter=True)
        event_joined = True
        # Check if entity exists in the event's mentions array
        # This is a simplified filter - assumes mentions field exists in JSON content
        filters.append(
            or_(
                EventORM.content.astext.contains(f'"{entity}"'),
                EventORM.content.astext.contains(f"'{entity}'"),
            )
        )

    # Filter by data provider/feed source (e.g., coindesk, coingecko, cointelegraph)
    # Use INNER JOIN for source to only get alerts with matching events
    if source:
        if not event_joined:
            query = query.join(EventORM, AlertORM.event_id == EventORM.id)
            event_joined = True
        filters.append(EventORM.source == source)

    # Filter by alert delivery channels (stored as JSON array)
    if channels:
        filters.append(AlertORM.channels.astext.contains(channels))

    if filters:
        query = query.where(and_(*filters))

    # Order by creation time (newest first)
    query = query.order_by(desc(AlertORM.created_at))

    # Apply pagination
    query = query.offset(skip).limit(min(limit, 100))

    # Execute
    result = await db.execute(query)
    return result.scalars().all()


def convert_alert_orm_to_schema(alert: AlertORM) -> Alert:
    """Convert Alert ORM model to Pydantic schema for API response.

    Args:
        alert: Alert ORM model instance

    Returns:
        Alert: Pydantic schema object
    """
    # Return basic alert without event enrichment
    # Note: Prefer convert_alert_with_event() for full data
    return Alert(
        alert_id=str(alert.id),
        created_at=alert.created_at.isoformat() if alert.created_at else "",
        title="Alert",  # Will be enriched with event data by caller
        priority=None,
        entity=None,
        status=alert.status or "pending",
        read_at=alert.sent_at.isoformat() if alert.sent_at else None,
    )


async def convert_alert_with_event(db: AsyncSession, alert: AlertORM) -> Alert:
    """Convert Alert ORM with enriched event data.

    Args:
        db: Database session
        alert: Alert ORM model instance

    Returns:
        Alert: Pydantic schema with event details
    """
    # Extract data from event content if available
    title = "Alert"
    priority = None
    entity = None

    # Only fetch event if we have an event_id
    if alert.event_id:
        try:
            result = await db.execute(
                select(EventORM).where(EventORM.id == alert.event_id)
            )
            event = result.scalars().first()

            if event:
                logger.debug(
                    f"[DEBUG] Found event {alert.event_id} for alert {alert.id}"
                )
                if event.content:
                    # Get title - try multiple fields to find actual alert content
                    title = (
                        event.content.get("title")
                        or event.content.get("body")
                        or event.content.get("summary")
                        or f"Event {alert.event_id}"
                    )

                    # Get priority from event content
                    priority = event.content.get("priority")

                    # Get primary entity/cryptocurrency mentioned
                    mentions = event.content.get("mentions", [])
                    entity = mentions[0] if mentions else None

                    logger.debug(
                        f"[DEBUG] Extracted title='{title}', priority={priority}, entity={entity}"
                    )
                else:
                    logger.warning(f"[⚠] Event {alert.event_id} has no content")
            else:
                logger.warning(
                    f"[⚠] Event {alert.event_id} not found for alert {alert.id}"
                )
        except Exception as e:
            logger.error(
                f"[❌] Error fetching event {alert.event_id} for alert {alert.id}: {e}"
            )
    else:
        logger.debug(f"[DEBUG] Alert {alert.id} has no event_id")

    return Alert(
        alert_id=str(alert.id),
        created_at=alert.created_at.isoformat() if alert.created_at else "",
        title=title,
        priority=priority,
        entity=entity,
        status=alert.status or "pending",
        read_at=alert.sent_at.isoformat() if alert.sent_at else None,
    )


@router.get("/history", response_model=List[Alert])
async def alert_history(
    start_date: Optional[datetime] = Query(None),
    end_date: Optional[datetime] = Query(None),
    priority: Optional[str] = Query(None),
    entity: Optional[str] = Query(
        None, description="Filter by token/entity name (e.g., 'Bitcoin', 'Ethereum')"
    ),
    source: Optional[str] = Query(
        None,
        description="Filter by data provider/feed (e.g., 'coindesk', 'coingecko', 'cointelegraph')",
    ),
    channels: Optional[str] = Query(
        None,
        description="Filter by delivery channel (e.g., 'email', 'telegram', 'sms')",
    ),
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=50),
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """Get alert history with filters and pagination.

    Query Parameters:
    - skip: Offset for pagination (default: 0)
    - limit: Number of alerts to return (default: 20, max: 50)
    - start_date: Filter alerts after this date (ISO format)
    - end_date: Filter alerts before this date (ISO format)
    - priority: Filter by priority (HIGH, MEDIUM, LOW)
    - entity: Filter by cryptocurrency/token name (e.g., Bitcoin, Ethereum, Solana)
    - source: Filter by data provider/feed (e.g., CoinDesk, CoinGecko, CoinMarketCap, Cointelegraph)
    - channels: Filter by how you receive alerts (email, telegram, sms, in-app, webhook)

    Returns:
        List of alerts for the current authenticated user
    """
    try:
        alerts = await get_alerts_query(
            db=db,
            user_id=current_user.id,
            start_date=start_date,
            end_date=end_date,
            priority=priority,
            entity=entity,
            source=source,
            channels=channels,
            skip=skip,
            limit=limit,
        )

        # Enrich alerts with event details
        enriched_alerts = []
        for alert in alerts:
            enriched = await convert_alert_with_event(db, alert)
            enriched_alerts.append(enriched)

        return enriched_alerts

    except Exception as e:
        logger.error(f"Error fetching alert history for user {current_user.id}: {e}")
        raise HTTPException(status_code=500, detail="Error fetching alert history")


@router.get("/{alert_id}", response_model=Alert)
async def get_alert(
    alert_id: int,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """Get a single alert by ID.

    Args:
        alert_id: Alert ID to retrieve

    Returns:
        Alert object or 404 if not found or not owned by user
    """
    try:
        # Query and verify ownership - allow personal alerts and broadcast alerts (user_id=0)
        result = await db.execute(
            select(AlertORM).where(
                and_(
                    AlertORM.id == alert_id,
                    (AlertORM.user_id == current_user.id)
                    | (AlertORM.user_id == 0)
                    | (AlertORM.user_id.is_(None)),
                )
            )
        )
        alert = result.scalars().first()

        if not alert:
            logger.warning(
                f"Alert {alert_id} not found or not owned by user {current_user.id}"
            )
            raise HTTPException(status_code=404, detail="Alert not found")

        # Enrich with event details
        enriched = await convert_alert_with_event(db, alert)
        return enriched

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching alert {alert_id}: {e}")
        raise HTTPException(status_code=500, detail="Error fetching alert")


@router.patch("/{alert_id}", response_model=Alert)
async def mark_alert_read(
    alert_id: int,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """Mark an alert as read.

    Args:
        alert_id: Alert ID to mark as read

    Returns:
        Updated alert object
    """
    try:
        # Query and verify ownership - allow personal alerts and broadcast alerts (user_id=0 or user_id=None)
        result = await db.execute(
            select(AlertORM).where(
                and_(
                    AlertORM.id == alert_id,
                    (AlertORM.user_id == current_user.id)
                    | (AlertORM.user_id == 0)
                    | (AlertORM.user_id.is_(None)),
                )
            )
        )
        alert = result.scalars().first()

        if not alert:
            logger.warning(
                f"Alert {alert_id} not found or not owned by user {current_user.id}"
            )
            raise HTTPException(status_code=404, detail="Alert not found")

        # Update status
        alert.status = "read"
        alert.sent_at = datetime.utcnow()

        await db.commit()
        await db.refresh(alert)

        logger.info(f"Alert {alert_id} marked as read by user {current_user.id}")
        # Return enriched alert with event details
        enriched = await convert_alert_with_event(db, alert)
        return enriched

    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        logger.error(f"Error marking alert {alert_id} as read: {e}")
        raise HTTPException(status_code=500, detail="Error updating alert")


@router.delete("/{alert_id}", response_model=AlertDismissResponse)
async def dismiss_alert(
    alert_id: int,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """
    Dismiss/delete an alert.

    P0 Security Fix: Verifies the alert belongs to the authenticated user

    Args:
        alert_id: Alert ID to dismiss

    Returns:
        Confirmation message
    """
    try:
        # Query and verify ownership - allow personal alerts and broadcast alerts (user_id=0 or user_id=None)
        result = await db.execute(
            select(AlertORM).where(
                and_(
                    AlertORM.id == alert_id,
                    (AlertORM.user_id == current_user.id)
                    | (AlertORM.user_id == 0)
                    | (AlertORM.user_id.is_(None)),
                )
            )
        )
        alert = result.scalars().first()

        if not alert:
            logger.warning(
                f"Alert {alert_id} not found or not owned by user {current_user.id}"
            )
            raise HTTPException(status_code=404, detail="Alert not found")

        # Delete
        await db.delete(alert)
        await db.commit()

        logger.info(f"Alert {alert_id} dismissed by user {current_user.id}")
        return AlertDismissResponse(detail="Alert dismissed successfully")

    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        logger.error(f"Error dismissing alert {alert_id}: {e}")
        raise HTTPException(status_code=500, detail="Error dismissing alert")


@router.get("/history/export", response_class=StreamingResponse)
async def export_alert_history_csv(
    start_date: Optional[datetime] = Query(None),
    end_date: Optional[datetime] = Query(None),
    priority: Optional[str] = Query(None),
    entity: Optional[str] = Query(None),
    source: Optional[str] = Query(None),
    channels: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """
    Export alert history as CSV.

    P0 Security Fix: Exports only alerts belonging to the authenticated user

    Query Parameters:
    - start_date: Filter alerts after this date (ISO format)
    - end_date: Filter alerts before this date (ISO format)
    - priority: Filter by priority (HIGH, MEDIUM, LOW)
    - entity: Filter by cryptocurrency/token (e.g., Bitcoin, Ethereum, Solana)
    - source: Filter by data provider/feed (e.g., coindesk, coingecko, cointelegraph, coinmarketcap)
    - channels: Filter by delivery channel (email, telegram, sms, in-app, webhook)

    Returns:
        CSV file download with alert history
    """
    try:
        alerts = await get_alerts_query(
            db=db,
            user_id=current_user.id,
            start_date=start_date,
            end_date=end_date,
            priority=priority,
            entity=entity,
            source=source,
            channels=channels,
            limit=10000,  # Allow larger export
        )

        # Build CSV
        def generate_csv():
            # Header
            fieldnames = [
                "alert_id",
                "created_at",
                "title",
                "priority",
                "status",
                "source",
                "channels",
            ]
            output = StringIO()
            writer = csv.DictWriter(output, fieldnames=fieldnames)
            writer.writeheader()

            # Data
            for alert in alerts:
                writer.writerow(
                    {
                        "alert_id": alert.id,
                        "created_at": (
                            alert.created_at.isoformat() if alert.created_at else ""
                        ),
                        "title": alert.alert_id,
                        "priority": alert.priority,
                        "status": alert.status,
                        "source": alert.source if hasattr(alert, "source") else "",
                        "channels": str(alert.channels) if alert.channels else "",
                    }
                )

            output.seek(0)
            yield output.read()

        logger.info(f"Alert history exported by user {current_user.id}")
        return StreamingResponse(
            generate_csv(),
            media_type="text/csv",
            headers={"Content-Disposition": "attachment; filename=alerts_export.csv"},
        )

    except Exception as e:
        logger.error(f"Error exporting alerts for user {current_user.id}: {e}")
        raise HTTPException(status_code=500, detail="Error exporting alerts")


# ============================================================
# DIAGNOSTIC ENDPOINTS - Admin only, for debugging alert system
# ============================================================


@router.get("/diagnostics/all", dependencies=[require_role("admin")])
async def get_all_alerts_diagnostic(
    limit: int = Query(100, ge=1, le=1000),
    skip: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
):
    """Admin-only endpoint to view all alerts in system (for debugging).

    Parameters:
    - limit: Maximum number of alerts to return (default: 100, max: 1000)
    - skip: Offset for pagination (default: 0)

    Returns:
        List of all alerts (personal and broadcast) with count
    """
    try:
        # Get total count
        count_result = await db.execute(select(AlertORM))
        total_count = len(count_result.scalars().all())

        # Get paginated results
        result = await db.execute(
            select(AlertORM)
            .order_by(desc(AlertORM.created_at))
            .offset(skip)
            .limit(min(limit, 1000))
        )
        alerts = result.scalars().all()

        return {
            "total": total_count,
            "returned": len(alerts),
            "skip": skip,
            "limit": limit,
            "alerts": [
                {
                    "id": alert.id,
                    "user_id": alert.user_id,
                    "event_id": alert.event_id,
                    "priority": alert.priority,
                    "status": alert.status,
                    "created_at": (
                        alert.created_at.isoformat() if alert.created_at else None
                    ),
                    "channels": alert.channels,
                }
                for alert in alerts
            ],
        }
    except Exception as e:
        logger.error(f"Error fetching diagnostic alerts: {e}")
        raise HTTPException(status_code=500, detail="Error fetching alerts")


@router.get("/diagnostics/user/{user_id}", dependencies=[require_role("admin")])
async def get_user_alerts_diagnostic(
    user_id: int,
    limit: int = Query(100, ge=1, le=1000),
    skip: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
):
    """Admin-only endpoint to view all alerts for specific user (for debugging).

    Parameters:
    - user_id: User ID to query
    - limit: Maximum number of alerts to return (default: 100, max: 1000)
    - skip: Offset for pagination (default: 0)

    Returns:
        List of alerts for user including broadcast alerts
    """
    try:
        # Get total count for this user (including broadcast)
        count_result = await db.execute(
            select(AlertORM).where(
                (AlertORM.user_id == user_id)
                | (AlertORM.user_id == 0)
                | (AlertORM.user_id.is_(None))
            )
        )
        total_count = len(count_result.scalars().all())

        # Get paginated results
        result = await db.execute(
            select(AlertORM)
            .where(
                (AlertORM.user_id == user_id)
                | (AlertORM.user_id == 0)
                | (AlertORM.user_id.is_(None))
            )
            .order_by(desc(AlertORM.created_at))
            .offset(skip)
            .limit(min(limit, 1000))
        )
        alerts = result.scalars().all()

        return {
            "user_id": user_id,
            "total": total_count,
            "returned": len(alerts),
            "skip": skip,
            "limit": limit,
            "alerts": [
                {
                    "id": alert.id,
                    "user_id": alert.user_id,
                    "event_id": alert.event_id,
                    "priority": alert.priority,
                    "status": alert.status,
                    "created_at": (
                        alert.created_at.isoformat() if alert.created_at else None
                    ),
                    "channels": alert.channels,
                    "is_broadcast": alert.user_id == 0,
                }
                for alert in alerts
            ],
        }
    except Exception as e:
        logger.error(f"Error fetching diagnostic alerts for user {user_id}: {e}")
        raise HTTPException(status_code=500, detail="Error fetching alerts")
