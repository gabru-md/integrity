from pydantic import Field, field_validator
from typing import Optional, Literal, List
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
    user_id: Optional[int] = Field(default=None, edit_enabled=False, ui_enabled=False)
    name: str = Field(
        description="A unique name for the project, used in event tags.",
        widget_enabled=True
    )
    project_type: Literal["Code", "DIY", "Other"] = Field(
        default="Other",
        widget_enabled=True,
        description="Broad category for the project"
    )
    focus_tags: List[str] = Field(
        default_factory=list,
        widget_enabled=True,
        description="Shared tags this project should emit so tickets, updates, skills, and promises line up."
    )
    start_date: datetime = Field(default_factory=datetime.now, description="When the project started")

    state: ProjectState = Field(
        default=ProjectState.ACTIVE,
        edit_enabled=True,
        widget_enabled=True,
        description="Current lifecycle state of the project: Active, On Hold, Completed, Archived"
    )
    last_updated: Optional[datetime] = Field(
        default=None,
        edit_enabled=False,
        widget_enabled=True,
        description="Most recent time the project timeline was updated"
    )
    progress_count: int = Field(
        default=0,
        description="Number of progress updates logged.",
        edit_enabled=False
    )

    @field_validator("focus_tags", mode="before")
    @classmethod
    def validate_focus_tags(cls, value):
        if value is None:
            return []
        if isinstance(value, str):
            return [item.strip().lower() for item in value.split(",") if item.strip()]
        return [str(item).strip().lower() for item in value if str(item).strip()]
