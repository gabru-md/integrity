from typing import Optional, List
from pydantic import Field
from datetime import datetime
from gabru.flask.model import WidgetUIModel

class BlogPost(WidgetUIModel):
    id: Optional[int] = Field(default=None, edit_enabled=False)
    title: str = Field(..., widget_enabled=True)
    slug: str = Field(..., description="URL-friendly identifier", widget_enabled=True)
    content: str = Field(..., description="Markdown content")
    tags: List[str] = Field(default_factory=list, widget_enabled=True)
    status: str = Field(default="draft", description="draft or published", widget_enabled=True)
    created_at: datetime = Field(default_factory=datetime.now, edit_enabled=False)
    updated_at: datetime = Field(default_factory=datetime.now, edit_enabled=False)
