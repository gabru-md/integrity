from pydantic import BaseModel, Field
from typing import Optional, List


class Event(BaseModel):
    id: Optional[int] = Field(default=None, ui_disabled=True)
    event_type: str = Field(..., ui_disabled=False)
    timestamp: Optional[int] = Field(default=None, ui_disabled=True)
    description: Optional[str] = Field(default="", ui_disabled=False)
    tags: Optional[List[str]] = Field(default_factory=list, ui_disabled=False)
