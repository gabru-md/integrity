from typing import Optional
from pydantic import Field
from datetime import datetime

from gabru.flask.model import WidgetUIModel


class Thought(WidgetUIModel):
    id: Optional[int] = Field(default=None, edit_enabled=False)
    message: str = Field(default=None, widget_enabled=True)
    created_at: Optional[datetime] = Field(default=None, edit_enabled=False, widget_enabled=True)
