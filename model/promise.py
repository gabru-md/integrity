from typing import Optional, List
from pydantic import Field
from datetime import datetime

from gabru.flask.model import WidgetUIModel


class Promise(WidgetUIModel):
    id: Optional[int] = Field(default=None, edit_enabled=False)
    name: str = Field(default=None, widget_enabled=True, description="Short name for the commitment")
    description: Optional[str] = Field(default=None, widget_enabled=True, description="Optional context explaining the promise")
    
    # frequency: once, daily, weekly, monthly
    frequency: str = Field(default="daily", widget_enabled=True, description="How often the promise is checked and reset")
    
    # target_event_tag or target_event_type - use one or both
    target_event_tag: Optional[str] = Field(default=None, widget_enabled=True, description="Tag that matching events must include")
    target_event_type: Optional[str] = Field(default=None, widget_enabled=True, description="Exact event type that matching events must use")
    
    required_count: int = Field(default=1, widget_enabled=True, description="How many matching events are required in each period")
    
    # status: active, fulfilled, broken, pending, paused
    status: str = Field(default="active", edit_enabled=False, widget_enabled=True, description="Current promise state such as active, fulfilled, or broken")
    
    current_count: int = Field(default=0, edit_enabled=False, widget_enabled=True, description="How many matching events have been counted in the current period")
    
    # Tracking
    streak: int = Field(default=0, edit_enabled=False, widget_enabled=True, description="Number of consecutive successful periods")
    best_streak: int = Field(default=0, edit_enabled=False, widget_enabled=True, description="Best streak reached so far")
    total_completions: int = Field(default=0, edit_enabled=False, widget_enabled=True, description="How many periods ended in success")
    total_periods: int = Field(default=0, edit_enabled=False, widget_enabled=True, description="How many periods have been evaluated")
    
    last_checked_at: Optional[datetime] = Field(default=None, edit_enabled=False, ui_enabled=True, description="Most recent time the promise was evaluated")
    next_check_at: Optional[datetime] = Field(default=None, edit_enabled=False, ui_enabled=True, description="Next scheduled evaluation time")

    created_at: datetime = Field(default_factory=datetime.now, edit_enabled=False, description="When the promise was created")
    updated_at: datetime = Field(default_factory=datetime.now, edit_enabled=False, description="When the promise was last updated")
