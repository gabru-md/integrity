from typing import Optional
from pydantic import BaseModel, Field
from datetime import datetime


class Contract(BaseModel):
    id: Optional[int] = Field(default=None, ui_disabled=True)
    name: str
    description: Optional[str]
    frequency: Optional[str]
    trigger_event: str
    conditions: str
    violation_message: str
    start_time: Optional[datetime]
    end_time: Optional[datetime]
    is_valid: bool = Field(..., ui_disabled=True)
