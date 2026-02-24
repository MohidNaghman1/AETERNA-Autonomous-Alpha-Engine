"""
SQLAlchemy Event ORM model for ingestion infrastructure.
Maps to the 'events' table in the database.
"""
from sqlalchemy import Column, String, DateTime, JSON,Integer
from app.config.db import Base

class EventORM(Base):
    __tablename__ = 'events'

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    source = Column(String, nullable=False, index=True)
    type = Column(String, nullable=False, index=True)
    timestamp = Column(DateTime, nullable=False, index=True)
    content = Column(JSON, nullable=False)
    raw = Column(JSON, nullable=True)

    def __repr__(self):
        return f"<EventORM(id={self.id}, source={self.source}, type={self.type}, timestamp={self.timestamp})>"
