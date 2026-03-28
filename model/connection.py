from datetime import datetime
from typing import Optional, List, Literal

from pydantic import Field

from gabru.flask.model import WidgetUIModel


class Connection(WidgetUIModel):
    id: Optional[int] = Field(default=None, edit_enabled=False)
    name: str = Field(default="", widget_enabled=True, description="Display name for the person or relationship you want to track.")
    relationship_type: Literal["Family", "Friend", "Partner", "Colleague", "Mentor", "Community", "Other"] = Field(
        default="Friend",
        widget_enabled=True,
        description="Broad relationship category used for coverage and reporting."
    )
    cadence_days: int = Field(
        default=14,
        widget_enabled=True,
        description="How many days should pass before this connection is considered overdue."
    )
    priority: Literal["High", "Medium", "Low"] = Field(
        default="Medium",
        widget_enabled=True,
        description="How important it is to maintain regular contact with this connection."
    )
    notes: str = Field(default="", description="Context, reminders, or relationship notes.", widget_enabled=False)
    tags: List[str] = Field(default_factory=list, widget_enabled=True, description="Optional labels such as close, family, work, or local.")
    active: bool = Field(default=True, widget_enabled=True, description="Whether this connection should be included in cadence checks.")
    created_at: datetime = Field(default_factory=datetime.now, edit_enabled=False, description="When the connection was added.")
    last_contact_at: Optional[datetime] = Field(
        default=None,
        edit_enabled=False,
        widget_enabled=True,
        description="Most recent logged interaction in this connection's ledger."
    )
