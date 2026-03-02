"""Alert API endpoints for listing, retrieving, marking as read, and dismissing alerts.

Provides REST endpoints for users to access their alert history with filtering and pagination.
All endpoints require authentication and enforce user ownership of alerts.
"""

from fastapi import APIRouter, HTTPException, Query, Depends, status
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, desc
from sqlalchemy.orm import Session
from app.config.db import AsyncSessionLocal
from app.shared.application.dependencies import get_db, get_current_user
from app.modules.alerting.infrastructure.models import Alert as AlertORM
from app.modules.alerting.presentation.schema import Alert, AlertDismissResponse
from datetime import datetime, timedelta
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
        entity: Filter by entity
        skip: Offset for pagination
        limit: Number of results (max 100)

    Returns:
        List of Alert ORM objects
    """
    # Start with base query
    query = select(AlertORM).where(AlertORM.user_id == user_id)

    # Apply filters
    filters = []
    if start_date:
        filters.append(AlertORM.created_at >= start_date)
    if end_date:
        filters.append(AlertORM.created_at <= end_date)
    if priority:
        filters.append(AlertORM.priority == priority)

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
    return Alert(
        alert_id=str(alert.id),
        created_at=alert.created_at.isoformat() if alert.created_at else "",
        title=alert.alert_id,
        priority=alert.priority,
        entity=None,  # Not in ORM model yet
        status=alert.status,
        read_at=alert.sent_at.isoformat() if alert.sent_at else None,
    )


@router.get("/history", response_model=List[Alert])
async def alert_history(
    start_date: Optional[datetime] = Query(None),
    end_date: Optional[datetime] = Query(None),
    priority: Optional[str] = Query(None),
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
            skip=skip,
            limit=limit,
        )

        return [convert_alert_orm_to_schema(alert) for alert in alerts]

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
        # Query and verify ownership
        result = await db.execute(
            select(AlertORM).where(
                and_(AlertORM.id == alert_id, AlertORM.user_id == current_user.id)
            )
        )
        alert = result.scalars().first()

        if not alert:
            logger.warning(
                f"Alert {alert_id} not found or not owned by user {current_user.id}"
            )
            raise HTTPException(status_code=404, detail="Alert not found")

        return convert_alert_orm_to_schema(alert)

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
        # Query and verify ownership
        result = await db.execute(
            select(AlertORM).where(
                and_(AlertORM.id == alert_id, AlertORM.user_id == current_user.id)
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
        return convert_alert_orm_to_schema(alert)

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
        # Query and verify ownership
        result = await db.execute(
            select(AlertORM).where(
                and_(AlertORM.id == alert_id, AlertORM.user_id == current_user.id)
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
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """
    Export alert history as CSV.

    P0 Security Fix: Exports only alerts belonging to the authenticated user

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
            limit=10000,  # Allow larger export
        )

        # Build CSV
        def generate_csv():
            # Header
            fieldnames = ["alert_id", "created_at", "title", "priority", "status"]
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
