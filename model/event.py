from pydantic import Field
from typing import Optional, List, Dict, Any
from datetime import datetime
from gabru.flask.model import WidgetUIModel


class Event(WidgetUIModel):
    id: Optional[int] = Field(default=None, edit_enabled=False)
    user_id: Optional[int] = Field(default=None, edit_enabled=False, ui_enabled=False)
    event_type: str = Field(default=None, widget_enabled=True, description="Main machine-readable event name such as learning:session")
    timestamp: Optional[datetime] = Field(default=None, edit_enabled=False, widget_enabled=True, description="When the event happened")
    description: Optional[str] = Field(default="", edit_enabled=True, widget_enabled=True, description="Human-readable summary of what happened")
    tags: Optional[List[str]] = Field(default_factory=list, edit_enabled=True, widget_enabled=True, description="Extra labels used for grouping, filtering, and skill or promise matching")
    payload: Dict[str, Any] = Field(default_factory=dict, widget_enabled=False, description="Optional structured context that travels with the event without replacing event_type or tags.")
