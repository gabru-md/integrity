from typing import Optional
from pydantic import Field
from datetime import datetime

from gabru.flask.model import UIModel


class Thought(UIModel):
    id: Optional[int] = Field(default=None, ui_disabled=True)
    message: str
    created_at: Optional[datetime] = Field(default=None, ui_disabled=True)
