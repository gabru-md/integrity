from pydantic import BaseModel
from typing import Any

class UIModel(BaseModel):
    """Base model that ensures all fields default to edit_enabled=False
    unless explicitly overridden."""

    def __init_subclass__(cls, **kwargs: Any):
        super().__init_subclass__(**kwargs)

        # Go through each field and ensure edit_enabled is set
        for name, field in cls.model_fields.items():
            if not field.json_schema_extra:  # initialize if empty
                field.json_schema_extra = {}

            # If no edit_enabled was provided, set it to True
            if "edit_enabled" not in field.json_schema_extra:
                field.json_schema_extra["edit_enabled"] = True


class WidgetUIModel(UIModel):
    def __init_subclass__(cls, **kwargs):
        super().__init_subclass__(**kwargs)
        for name, field in cls.model_fields.items():
            if not field.json_schema_extra:  # initialize if empty
                field.json_schema_extra = {}

            # If no edit_enabled was provided, set it to False
            if "widget_enabled" not in field.json_schema_extra:
                field.json_schema_extra["widget_enabled"] = False
