from typing import Optional
from pydantic import Field
from datetime import datetime

from gabru.flask.model import UIModel


class Contract(UIModel):
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
