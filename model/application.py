from typing import Optional
from pydantic import BaseModel, Field

class Application(BaseModel):
    id: Optional[int] = None
    name: str = Field(..., description="Unique name of the application")
    is_active: bool = Field(True, description="Whether the application is enabled")
    description: Optional[str] = Field(None, description="Description of the application")
