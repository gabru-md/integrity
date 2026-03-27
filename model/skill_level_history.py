from datetime import datetime
from typing import Optional

from pydantic import Field

from gabru.flask.model import WidgetUIModel


class SkillLevelHistory(WidgetUIModel):
    id: Optional[int] = Field(default=None, edit_enabled=False)
    skill_id: int = Field(default=0, widget_enabled=False, description="Skill id linked to the level-up event")
    skill_name: str = Field(default="", widget_enabled=True, description="Display name of the skill")
    level: int = Field(default=1, widget_enabled=True, description="Level reached")
    total_xp: int = Field(default=0, widget_enabled=True, description="Total XP when this level was reached")
    reached_at: datetime = Field(default_factory=datetime.now, edit_enabled=False, widget_enabled=True)
    summary: str = Field(default="", widget_enabled=True, description="Human-friendly level-up summary")
