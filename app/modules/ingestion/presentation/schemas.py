from pydantic import BaseModel
from typing import Any, Dict, Optional
from datetime import datetime

class EventIn(BaseModel):
    id: str
    source: str
    type: str
    timestamp: datetime
    content: Dict[str, Any]
    raw: Optional[Any] = None

class EventOut(EventIn):
    pass
