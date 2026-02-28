from pydantic import BaseModel
from typing import Optional
from datetime import datetime

class Alert(BaseModel):
    alert_id: str
    created_at: str  # ISO format string
    title: str
    priority: Optional[str] = None
    entity: Optional[str] = None
    status: Optional[str] = None
    read_at: Optional[str] = None

class AlertDismissResponse(BaseModel):
    detail: str
