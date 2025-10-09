from typing import Optional
from pydantic import Field
from datetime import datetime

from gabru.flask.model import WidgetUIModel


class Contract(WidgetUIModel):
    id: Optional[int] = Field(default=None, edit_enabled=False)
    name: str = Field(default=None, widget_enabled=True)
    description: Optional[str] = Field(default=None, widget_enabled=True)
    frequency: Optional[str]
    trigger_event: str = Field(default=None)
    conditions: str = Field(default=None, widget_enabled=True)
    violation_message: str
    start_time: Optional[datetime]
    end_time: Optional[datetime]
    last_run_date: Optional[datetime] = Field(default=None, edit_enabled=False)
    next_run_date: Optional[datetime] = Field(default=None)
