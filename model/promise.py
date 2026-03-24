from typing import Optional, List
from pydantic import Field
from datetime import datetime

from gabru.flask.model import WidgetUIModel


class Promise(WidgetUIModel):
    id: Optional[int] = Field(default=None, edit_enabled=False)
    name: str = Field(default=None, widget_enabled=True)
    description: Optional[str] = Field(default=None, widget_enabled=True)
    
    # frequency: once, daily, weekly, monthly
    frequency: str = Field(default="daily", widget_enabled=True)
    
    # target_event_tag or target_event_type - use one or both
    target_event_tag: Optional[str] = Field(default=None, widget_enabled=True)
    target_event_type: Optional[str] = Field(default=None, widget_enabled=True)
    
    required_count: int = Field(default=1, widget_enabled=True)
    
    # status: active, fulfilled, broken, pending, paused
    status: str = Field(default="active", edit_enabled=False, widget_enabled=True)
    
    # Tracking
    streak: int = Field(default=0, edit_enabled=False, widget_enabled=True)
    best_streak: int = Field(default=0, edit_enabled=False, widget_enabled=True)
    total_completions: int = Field(default=0, edit_enabled=False, widget_enabled=True)
    total_periods: int = Field(default=0, edit_enabled=False, widget_enabled=True)
    
    last_checked_at: Optional[datetime] = Field(default=None, edit_enabled=False, ui_enabled=True)
    next_check_at: Optional[datetime] = Field(default=None, edit_enabled=False, ui_enabled=True)
    
    created_at: datetime = Field(default_factory=datetime.now, edit_enabled=False)
    updated_at: datetime = Field(default_factory=datetime.now, edit_enabled=False)
