from datetime import datetime
from enum import Enum
from typing import Optional

from pydantic import Field

from gabru.flask.model import WidgetUIModel


class AgentRunStatus(str, Enum):
    QUEUED = "queued"
    CLAIMED = "claimed"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class AgentRun(WidgetUIModel):
    id: Optional[int] = Field(default=None, edit_enabled=False)
    user_id: Optional[int] = Field(default=None, edit_enabled=False, ui_enabled=False)
    project_id: int = Field(default=0, widget_enabled=True, description="Project that owns this agent run")
    ticket_id: int = Field(default=0, widget_enabled=True, description="Kanban ticket that requested the run")
    workspace_key: str = Field(default="", widget_enabled=True, description="Logical workspace name resolved by the local worker")
    agent_kind: str = Field(default="dry-run", widget_enabled=True, description="Local executor requested for the worker")
    status: AgentRunStatus = Field(default=AgentRunStatus.QUEUED, widget_enabled=True, description="Current worker lifecycle state")
    prompt: str = Field(default="", widget_enabled=False, description="Complete task prompt sent to the worker")
    result_summary: str = Field(default="", widget_enabled=True, description="Worker result summary")
    changed_files: list[str] = Field(default_factory=list, widget_enabled=True, description="Files reported by the worker")
    error_message: str = Field(default="", widget_enabled=True, description="Failure detail reported by the worker")
    worker_name: str = Field(default="", widget_enabled=True, description="Worker that claimed the run")
    created_at: datetime = Field(default_factory=datetime.now, edit_enabled=False, widget_enabled=True)
    claimed_at: Optional[datetime] = Field(default=None, edit_enabled=False, widget_enabled=True)
    started_at: Optional[datetime] = Field(default=None, edit_enabled=False, widget_enabled=True)
    completed_at: Optional[datetime] = Field(default=None, edit_enabled=False, widget_enabled=True)
    updated_at: datetime = Field(default_factory=datetime.now, edit_enabled=False, widget_enabled=True)
