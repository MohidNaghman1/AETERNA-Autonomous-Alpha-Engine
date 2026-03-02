"""Pydantic schemas for alert API endpoints.

Defines request/response models for alert-related API operations.
"""

from pydantic import BaseModel
from typing import Optional
from datetime import datetime


class Alert(BaseModel):
    """Alert response schema.

    Attributes:
        alert_id: Unique alert identifier
        created_at: ISO format creation timestamp
        title: Alert title
        priority: Priority level (HIGH, MEDIUM, LOW)
        entity: Associated cryptocurrency entity
        status: Alert status (pending, sent, failed)
        read_at: ISO format timestamp when read, or None if unread
    """

    alert_id: str
    created_at: str
    title: str
    priority: Optional[str] = None
    entity: Optional[str] = None
    status: Optional[str] = None
    read_at: Optional[str] = None


class AlertDismissResponse(BaseModel):
    """Response when alert is dismissed.

    Attributes:
        detail: Status message
    """

    detail: str
