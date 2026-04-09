from typing import Optional, Dict, Any, List, Literal

from pydantic import Field

from gabru.flask.model import WidgetUIModel


BrowserActionType = Literal[
    "trigger_activity",
    "save_current_page",
    "capture_selection",
    "open_quick_log",
    "start_focus_session",
    "end_focus_session",
    "save_to_project",
]

BrowserActionTargetType = Literal["activity", "event", "project_update", "quick_log"]


class BrowserAction(WidgetUIModel):
    id: Optional[int] = Field(default=None, edit_enabled=False)
    user_id: Optional[int] = Field(default=None, edit_enabled=False, ui_enabled=False)
    name: str = Field(default="", widget_enabled=True, description="Human-readable label shown in Rasbhari and later in the extension, such as Save Docs Research.")
    browser_action: BrowserActionType = Field(default="trigger_activity", widget_enabled=True, description="The generic browser-side action the extension understands.")
    target_type: BrowserActionTargetType = Field(default="activity", widget_enabled=True, description="What Rasbhari should trigger when this browser action is used.")
    description: Optional[str] = Field(default="", widget_enabled=True, description="Short explanation of what this action is meant to do.")
    target_activity_id: Optional[int] = Field(default=None, widget_type="select", widget_options=[], description="Optional Activity to trigger when target type is activity.")
    target_project_id: Optional[int] = Field(default=None, widget_type="select", widget_options=[], description="Optional Project to use when this action should create a project update or save into project context.")
    target_event_type: Optional[str] = Field(default="", description="Fallback event type to emit when target type is event and no Activity is used.")
    target_tags: List[str] = Field(default_factory=list, widget_enabled=True, description="Tags Rasbhari should attach when this action creates an event-backed capture.")
    target_description: Optional[str] = Field(default="", description="Optional default human-readable description Rasbhari can use when this action creates an event or project update.")
    default_payload: Dict[str, Any] = Field(default_factory=dict, widget_enabled=False, description="Structured default payload fields to merge into extension-supplied browser context.")
    enabled: bool = Field(default=True, widget_enabled=True, description="Whether this action should be available to the browser extension when sync APIs land.")
