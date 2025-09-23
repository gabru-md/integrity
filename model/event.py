from pydantic import BaseModel
from typing import Optional, List

class Event(BaseModel):
    id: Optional[int] = None
    event_type: str
    timestamp: int
    description: Optional[str] = ""
    tags: Optional[List] = []