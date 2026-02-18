from sqlalchemy import Column, Integer, String, DateTime, Float, JSON, Text
from datetime import datetime
from app.config.db import Base

class Event(Base):
    __tablename__ = "events"
    id = Column(Integer, primary_key=True, index=True)
    event_type = Column(String, nullable=False)
    source = Column(String, nullable=False)
    content = Column(Text, nullable=False)
    event_metadata = Column(JSON, nullable=True)  # Renamed from 'metadata' to 'event_metadata'
    score = Column(Float, nullable=True)
    priority = Column(Integer, nullable=True)
    timestamp = Column(DateTime, default=datetime.utcnow)
