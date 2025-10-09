from typing import Optional
from pydantic import Field

from gabru.flask.model import WidgetUIModel


class Shortcut(WidgetUIModel):
    id: Optional[int] = Field(default=None, ui_disabled=True)
    name: str = Field(default=None, widget_enabled=True)
    event_type: str = Field(default=None, widget_enabled=True)
    description: str = Field(default=None, widget_enabled=True)
    filename: str = Field(default=None, widget_enabled=False, ui_disabled=True, download_enabled=True)
    signed: bool = Field(deafult=False, widget_enabled=False, ui_disabled=True)
