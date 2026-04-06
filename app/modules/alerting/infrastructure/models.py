"""SQLAlchemy models for alert persistence.

Defines the database schema for storing alert records.
"""

from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, JSON
from datetime import datetime
from app.config.db import Base


class Alert(Base):
    """Alert database model.

    Stores alert records with delivery status and channel information.

    Attributes:
        id: Primary key
        user_id: Foreign key to users table
        event_id: Foreign key to events table
        channels: JSON array of delivery channels
        status: Alert status (pending, sent, failed)
        sent_at: Timestamp when alert was successfully sent
        created_at: Timestamp when alert was created
    """

    __tablename__ = "alerts"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(
        Integer, ForeignKey("users.id"), nullable=True
    )  # System alerts may not have user_id
    event_id = Column(
        Integer, ForeignKey("events.id"), nullable=True
    )  # System alerts may not have event_id
    channels = Column(JSON, nullable=True)
    priority = Column(
        String, default="MEDIUM", index=True
    )  # CRITICAL, HIGH, MEDIUM, LOW
    status = Column(String, default="pending")
    sent_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
