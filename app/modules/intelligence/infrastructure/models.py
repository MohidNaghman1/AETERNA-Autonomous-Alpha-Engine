"""
SQLAlchemy model for processed (scored) events
"""
from sqlalchemy import Column, Integer, String, Float, DateTime, JSON, Index
from app.config.db import Base
from datetime import datetime


class ProcessedEvent(Base):
    __tablename__ = 'processed_events'

    id = Column(String, primary_key=True)  # Use event id from source
    user_id = Column(String, index=True)
    timestamp = Column(DateTime, default=datetime.utcnow, index=True)
    priority = Column(String, index=True)
    score = Column(Float)
    multi_source = Column(Integer)
    engagement = Column(Integer)
    bot = Column(Integer)
    dedup = Column(Integer)
    event_data = Column(JSON)  # Store original event

    __table_args__ = (
        Index('ix_priority_timestamp_user', 'priority', 'timestamp', 'user_id'),
    )

# Retention policy: To be enforced by a scheduled cleanup task (not in model)
# Example cleanup query:
# session.query(ProcessedEvent).filter(ProcessedEvent.timestamp < datetime.utcnow() - timedelta(days=7)).delete()
