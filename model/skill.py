from typing import Optional

from pydantic import Field, field_validator

from gabru.flask.model import WidgetUIModel


class Skill(WidgetUIModel):
    id: Optional[int] = Field(default=None, edit_enabled=False)
    name: str = Field(default="", widget_enabled=True, description="Skill name used for tag matching, e.g. Python")
    level: int = Field(default=1, edit_enabled=False, widget_enabled=True, description="Current derived level")
    total_xp: int = Field(default=0, widget_enabled=True, description="Total experience points accumulated for the skill")
    requirement: str = Field(default="", widget_enabled=True, description="Requirement to unlock the next level")

    @field_validator("name")
    @classmethod
    def validate_name(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("name is required")
        return value

    @field_validator("level")
    @classmethod
    def validate_level(cls, value: int) -> int:
        return max(1, value)

    @field_validator("total_xp")
    @classmethod
    def validate_total_xp(cls, value: int) -> int:
        return max(0, value)
