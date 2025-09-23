from typing import Optional
from pydantic import BaseModel
from datetime import datetime


class Contract(BaseModel):
    id: Optional[int] = None
    name: str
    description: Optional[str] = ""
    frequency: Optional[str] = "ad-hoc"
    trigger_event: str
    conditions: str
    violation_message: str
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    is_valid: bool