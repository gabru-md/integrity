from pydantic import BaseModel
from typing import Any


class UIModel(BaseModel):
    """Base model that ensures all fields default to ui_disabled=False
    unless explicitly overridden."""

    def __init_subclass__(cls, **kwargs: Any):
        super().__init_subclass__(**kwargs)

        # Go through each field and ensure ui_disabled is set
        for name, field in cls.model_fields.items():
            if not field.json_schema_extra:  # initialize if empty
                field.json_schema_extra = {}

            # If no ui_disabled was provided, set it to False
            if "ui_disabled" not in field.json_schema_extra:
                field.json_schema_extra["ui_disabled"] = False
