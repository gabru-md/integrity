from datetime import datetime
from enum import Enum
from typing import Optional

from pydantic import Field

from gabru.flask.model import WidgetUIModel


class KanbanTicketState(str, Enum):
    BACKLOG = "backlog"
    PRIORITIZED = "prioritized"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    SHIPPED = "shipped"


class KanbanTicket(WidgetUIModel):
    id: Optional[int] = Field(default=None, edit_enabled=False)
    user_id: Optional[int] = Field(default=None, edit_enabled=False, ui_enabled=False)
    project_id: int = Field(default=0, widget_enabled=True, description="Project that owns this ticket")
    title: str = Field(default="", widget_enabled=True, description="Short ticket title shown on the board")
    description: Optional[str] = Field(default="", widget_enabled=True, description="Optional ticket detail")
    state: KanbanTicketState = Field(default=KanbanTicketState.BACKLOG, widget_enabled=True, description="Current workflow state")
    is_archived: bool = Field(default=False, widget_enabled=True, description="Whether the ticket is archived and hidden from the project board")
    created_at: datetime = Field(default_factory=datetime.now, edit_enabled=False, widget_enabled=True, description="When the ticket was created")
    updated_at: datetime = Field(default_factory=datetime.now, edit_enabled=False, widget_enabled=True, description="When the ticket was last updated")
    state_changed_at: datetime = Field(default_factory=datetime.now, edit_enabled=False, widget_enabled=True, description="When the workflow state last changed")
