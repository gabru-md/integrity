from pydantic import Field
from typing import Optional, List
from datetime import datetime
from gabru.flask.model import WidgetUIModel


class Event(WidgetUIModel):
    id: Optional[int] = Field(default=None, edit_enabled=False)
    event_type: str = Field(default=None, widget_enabled=True)
    timestamp: Optional[datetime] = Field(default=None, edit_enabled=False, widget_enabled=True)
    description: Optional[str] = Field(default="", edit_enabled=False, widget_enabled=True)
    tags: Optional[List[str]] = Field(default_factory=list, edit_enabled=False, widget_enabled=True)
