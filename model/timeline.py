from pydantic import Field
from datetime import datetime
from gabru.flask.model import WidgetUIModel
from typing import Optional, Literal


class TimelineItem(WidgetUIModel):
    """Data model for a timeline update or blog post linked to a project."""
    id: Optional[int] = Field(default=None, edit_enabled=False)
    user_id: Optional[int] = Field(default=None, edit_enabled=False, ui_enabled=False)
    project_id: int = Field(..., description="ID of the project this item belongs to", widget_enabled=False)
    title: Optional[str] = Field(default=None, description="Optional headline for richer narrative entries", widget_enabled=True)
    content: str = Field(..., description="The content of the update or blog post")
    blog_post_id: Optional[int] = Field(default=None, edit_enabled=False, widget_enabled=False, description="Linked blog post when this timeline item points at a real blog entry")
    blog_slug: Optional[str] = Field(default=None, edit_enabled=False, widget_enabled=False, description="Linked blog slug when this timeline item points at a real blog entry")
    timestamp: datetime = Field(default_factory=datetime.now, edit_enabled=False, widget_enabled=True)
    item_type: Literal["Update", "Blog"] = Field(default="Update", widget_enabled=True)
