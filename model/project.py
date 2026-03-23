from pydantic import Field
from typing import Optional, Literal
from datetime import datetime
from enum import Enum
from gabru.flask.model import WidgetUIModel


class ProjectState(str, Enum):
    """Enumeration for the possible states of a project."""
    ACTIVE = "Active"
    ON_HOLD = "On Hold"
    COMPLETED = "Completed"
    ARCHIVED = "Archived"


class Project(WidgetUIModel):
    """Data model for a project, including its state and progress."""
    id: Optional[int] = Field(default=None, edit_enabled=False)
    name: str = Field(
        description="A unique name for the project, used in event tags.",
        widget_enabled=True
    )
    project_type: Literal["Code", "DIY", "Other"] = Field(
        default="Other",
        widget_enabled=True
    )
    start_date: datetime = Field(default_factory=datetime.now)

    state: ProjectState = Field(
        default=ProjectState.ACTIVE,
        edit_enabled=False,
        widget_enabled=True
    )
    last_updated: Optional[datetime] = Field(
        default=None,
        edit_enabled=False,
        widget_enabled=True
    )
    progress_count: int = Field(
        default=0,
        description="Number of progress updates logged.",
        edit_enabled=False
    )
