from typing import Optional
from datetime import datetime

from pydantic import Field

from gabru.flask.model import UIModel


class Notification(UIModel):
    id: Optional[int] = Field(default=None, edit_enabled=False)
    user_id: Optional[int] = Field(default=None, widget_enabled=False, ui_enabled=False)
    title: Optional[str] = None
    notification_data: str
    href: Optional[str] = None
    notification_type: str = "ntfy"
    notification_class: str = "today"
    is_read: bool = Field(default=False, edit_enabled=False)
    created_at: Optional[datetime] = Field(default=None, edit_enabled=False)
