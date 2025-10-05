from typing import Optional
from pydantic import Field
from datetime import datetime

from gabru.flask.model import WidgetUIModel


class Thought(WidgetUIModel):
    id: Optional[int] = Field(default=None, ui_disabled=True)
    message: str = Field(default=None, widget_enabled=True)
    created_at: Optional[datetime] = Field(default=None, ui_disabled=True, widget_enabled=True)
