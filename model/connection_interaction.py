from datetime import datetime
from typing import Optional, List, Literal

from pydantic import Field

from gabru.flask.model import WidgetUIModel


class ConnectionInteraction(WidgetUIModel):
    id: Optional[int] = Field(default=None, edit_enabled=False)
    connection_id: int = Field(default=0, widget_enabled=False, description="ID of the connection this interaction belongs to.")
    connection_name: str = Field(default="", widget_enabled=True, description="Display name copied from the linked connection for easier scanning.")
    interaction_type: Literal["Call", "Text", "Meetup", "Video", "Email", "Gift", "Support", "Other"] = Field(
        default="Text",
        widget_enabled=True,
        description="Primary form of the interaction."
    )
    medium: str = Field(default="", widget_enabled=True, description="Secondary medium detail such as WhatsApp, Phone, In Person, or Slack.")
    duration_minutes: int = Field(default=0, widget_enabled=True, description="Approximate time spent on the interaction.")
    quality_score: int = Field(default=3, widget_enabled=True, description="How meaningful the interaction felt on a 1 to 5 scale.")
    notes: str = Field(default="", widget_enabled=False, description="Short notes about what happened or what matters next.")
    tags: List[str] = Field(default_factory=list, widget_enabled=True, description="Optional labels such as family, repair, support, or celebration.")
    created_at: datetime = Field(default_factory=datetime.now, edit_enabled=False, widget_enabled=True, description="When the interaction happened.")
