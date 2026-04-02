from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import Field, field_validator

from gabru.flask.model import UIModel


class ImportRecord(UIModel):
    id: Optional[int] = Field(default=None, edit_enabled=False)
    user_id: int = Field(default=0, edit_enabled=False, ui_enabled=False)
    source_type: str = Field(default="", description="Normalized source family such as calendar, device, or webhook")
    source_name: str = Field(default="", description="Concrete adapter or feed name within the source family")
    external_id: str = Field(default="", description="Stable id from the upstream integration source")
    fingerprint: str = Field(default="", description="Deterministic fingerprint used when upstream ids are weak or missing")
    occurred_at: datetime = Field(default_factory=datetime.now, description="When the imported record originally happened")
    title: str = Field(default="", description="Short human-readable summary from the source")
    description: Optional[str] = Field(default="", description="Optional source description or body")
    tags: List[str] = Field(default_factory=list, description="Normalized tags carried through to the event bus")
    raw_payload: Dict[str, Any] = Field(default_factory=dict, description="Stored raw source payload for future adapters and debugging")
    normalized_event_type: str = Field(default="imported:event", description="Event type emitted into Rasbhari for this record")
    imported_event_id: Optional[int] = Field(default=None, edit_enabled=False, description="Event id emitted into the event bus for this import")
    created_at: datetime = Field(default_factory=datetime.now, edit_enabled=False, description="When Rasbhari stored the import record")

    @field_validator("source_type", "source_name", "external_id", "fingerprint", "title", "normalized_event_type")
    @classmethod
    def validate_text_fields(cls, value: str) -> str:
        return (value or "").strip()

    @field_validator("tags", mode="before")
    @classmethod
    def validate_tags(cls, value):
        if value is None:
            return []
        if isinstance(value, str):
            return [item.strip() for item in value.split(",") if item.strip()]
        return [str(item).strip() for item in value if str(item).strip()]
