from pydantic import Field
from typing import Optional, Dict, Any, List
from gabru.flask.model import WidgetUIModel


class Activity(WidgetUIModel):
    id: Optional[int] = Field(default=None, edit_enabled=False)
    name: str = Field(default=None, widget_enabled=True, description="Display name for the activity (e.g., 'Clean Kitchen')")
    event_type: str = Field(default=None, widget_enabled=True, description="The type of event to emit (e.g., 'kitchen:cleaned')")
    description: Optional[str] = Field(default="", widget_enabled=True,
                                        description="Optional description for the activity")
    default_payload: Optional[Dict[str, Any]] = Field(default_factory=dict, widget_enabled=False,
                                                        description="Default JSON payload to include with the event")
    tags: List[str] = Field(default_factory=list, widget_enabled=True, description="List of tags for the event")
