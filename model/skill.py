from typing import Optional, List

from pydantic import Field, field_validator

from gabru.flask.model import WidgetUIModel


class Skill(WidgetUIModel):
    id: Optional[int] = Field(default=None, edit_enabled=False)
    user_id: Optional[int] = Field(default=None, edit_enabled=False, ui_enabled=False)
    name: str = Field(default="", widget_enabled=True, description="Display name for the skill, e.g. Python")
    tag_key: str = Field(default="", widget_enabled=True, description="Primary tag key used for matching, e.g. python or counterstrike")
    aliases: List[str] = Field(default_factory=list, widget_enabled=True, description="Optional comma-separated aliases such as cs2, counter-strike")
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

    @field_validator("tag_key")
    @classmethod
    def validate_tag_key(cls, value: str) -> str:
        return value.strip()

    @field_validator("aliases", mode="before")
    @classmethod
    def validate_aliases(cls, value):
        if value is None:
            return []
        if isinstance(value, str):
            return [item.strip() for item in value.split(",") if item.strip()]
        return value

    @field_validator("level")
    @classmethod
    def validate_level(cls, value: int) -> int:
        return max(1, value)

    @field_validator("total_xp")
    @classmethod
    def validate_total_xp(cls, value: int) -> int:
        return max(0, value)
