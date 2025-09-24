from typing import Optional
from datetime import datetime

from pydantic import BaseModel


class Notification(BaseModel):
    id: Optional[int] = None
    notification_data: str
    notification_type: str = "default"
    created_at: Optional[datetime] = None
