from typing import Optional, List
from pydantic import Field
from datetime import datetime
from gabru.flask.model import WidgetUIModel

class BlogPost(WidgetUIModel):
    id: Optional[int] = Field(default=None, edit_enabled=False)
    title: str = Field(..., widget_enabled=True, description="Title shown in the blog list and on the post page")
    slug: str = Field(..., description="URL-friendly identifier", widget_enabled=False)
    content: str = Field(..., description="Markdown content",widget_enabled=False)
    tags: List[str] = Field(default_factory=list, widget_enabled=True, description="Labels used to group related posts")
    status: str = Field(default="draft", description="Whether the post is a draft or published", widget_enabled=True)
    created_at: datetime = Field(default_factory=datetime.now, edit_enabled=False, description="When the post was first created")
    updated_at: datetime = Field(default_factory=datetime.now, edit_enabled=False, description="When the post was last edited")
