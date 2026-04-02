from typing import Optional
from datetime import datetime

from pydantic import Field

from gabru.flask.model import UIModel


class Notification(UIModel):
    id: Optional[int] = Field(default=None, edit_enabled=False)
    title: Optional[str] = None
    notification_data: str
    notification_type: str = "ntfy"
    notification_class: str = "today"
    created_at: Optional[datetime] = Field(default=None, edit_enabled=False)
