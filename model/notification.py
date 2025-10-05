from typing import Optional
from datetime import datetime

from pydantic import Field

from gabru.flask.model import UIModel


class Notification(UIModel):
    id: Optional[int] = Field(default=None, ui_disabled=True)
    notification_data: str
    notification_type: str = "default"
    created_at: Optional[datetime] = Field(default=None, ui_disabled=True)
