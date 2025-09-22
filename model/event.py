from pydantic import BaseModel
from typing import Optional, List

# Ideally this should be shared between apps

class Event(BaseModel):
    id: Optional[int] = None
    event_type: str
    timestamp: int
    description: Optional[str] = ""
    tags: Optional[List] = []