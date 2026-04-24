"""Pydantic schemas for alert API endpoints.

Defines request/response models for alert-related API operations.
"""

from pydantic import BaseModel
from typing import Optional


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
        event_id: (Optional) Linked event ID
        source: (Optional) Data provider/feed source
        event_type: (Optional) Type of event (news, price, etc)
        event_timestamp: (Optional) When the event occurred
        content: (Optional) Full event content with metadata (hashtags, mentions, urls, categories, etc)
    """

    alert_id: str
    created_at: str
    title: str
    priority: Optional[str] = None
    entity: Optional[str] = None
    status: Optional[str] = None
    read_at: Optional[str] = None
    event_id: Optional[int] = None
    source: Optional[str] = None
    event_type: Optional[str] = None
    event_timestamp: Optional[str] = None
    content: Optional[dict] = None


class AlertDismissResponse(BaseModel):
    """Response when alert is dismissed.

    Attributes:
        detail: Status message
    """

    detail: str
