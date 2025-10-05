from pydantic import Field
from typing import Optional, List

from gabru.flask.model import WidgetUIModel


class Event(WidgetUIModel):
    id: Optional[int] = Field(default=None, ui_disabled=True)
    event_type: str = Field(default=None, widget_enabled=True)
    timestamp: Optional[int] = Field(default=None, ui_disabled=True, widget_enabled=True)
    description: Optional[str] = Field(default="", ui_disabled=False, widget_enabled=True)
    tags: Optional[List[str]] = Field(default_factory=list, ui_disabled=False, widget_enabled=True)
