from __future__ import annotations

import hashlib
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Optional, Protocol

from pydantic import BaseModel, Field, field_validator

from model.event import Event
from model.import_record import ImportRecord
from services.events import EventService
from services.import_records import ImportRecordService


class NormalizedImportItem(BaseModel):
    source_type: str
    source_name: str
    external_id: Optional[str] = None
    occurred_at: datetime
    title: str
    description: Optional[str] = ""
    tags: list[str] = Field(default_factory=list)
    raw_payload: dict[str, Any] = Field(default_factory=dict)
    normalized_event_type: str = "imported:event"

    @field_validator("source_type", "source_name", "title", "normalized_event_type")
    @classmethod
    def validate_text(cls, value: str) -> str:
        return (value or "").strip()

    @field_validator("tags", mode="before")
    @classmethod
    def validate_tags(cls, value):
        if value is None:
            return []
        if isinstance(value, str):
            return [item.strip() for item in value.split(",") if item.strip()]
        return [str(item).strip() for item in value if str(item).strip()]


class ImportSourceAdapter(Protocol):
    def fetch_records(self, user_id: int, since: Optional[datetime] = None) -> list[NormalizedImportItem]:
        ...


@dataclass
class ImportBatchResult:
    source_type: str
    source_name: str
    fetched: int = 0
    imported: int = 0
    skipped: int = 0
    emitted_events: int = 0


class ImportPipelineService:
    def __init__(
        self,
        import_record_service: Optional[ImportRecordService] = None,
        event_service: Optional[EventService] = None,
    ):
        self.import_record_service = import_record_service or ImportRecordService()
        self.event_service = event_service or EventService()

    def import_from_adapter(
        self,
        *,
        user_id: int,
        adapter: ImportSourceAdapter,
        since: Optional[datetime] = None,
        emit_events: bool = True,
    ) -> ImportBatchResult:
        records = adapter.fetch_records(user_id=user_id, since=since)
        if not records:
            return ImportBatchResult(source_type="", source_name="", fetched=0)

        first = records[0]
        result = ImportBatchResult(source_type=first.source_type, source_name=first.source_name, fetched=len(records))

        for item in records:
            record = self._to_import_record(user_id=user_id, item=item)
            if self._already_imported(record):
                result.skipped += 1
                continue

            created_id = self.import_record_service.create(record)
            if not created_id:
                result.skipped += 1
                continue

            result.imported += 1
            record.id = created_id
            if emit_events:
                event = self._to_event(user_id=user_id, record=record)
                event_id = self.event_service.create(event)
                if event_id:
                    result.emitted_events += 1
                    record.imported_event_id = event_id
                    self.import_record_service.update(record)

        return result

    def _already_imported(self, record: ImportRecord) -> bool:
        if record.external_id:
            existing = self.import_record_service.get_by_source_key(
                user_id=record.user_id,
                source_type=record.source_type,
                source_name=record.source_name,
                external_id=record.external_id,
            )
            if existing:
                return True
        return self.import_record_service.get_by_fingerprint(
            user_id=record.user_id,
            source_type=record.source_type,
            source_name=record.source_name,
            fingerprint=record.fingerprint,
        ) is not None

    def _to_import_record(self, *, user_id: int, item: NormalizedImportItem) -> ImportRecord:
        source_type = self.normalize_source_value(item.source_type)
        source_name = self.normalize_source_value(item.source_name)
        tags = self.normalize_tags(item.tags)
        payload = item.raw_payload or {}
        fingerprint = self.build_fingerprint(
            source_type=source_type,
            source_name=source_name,
            external_id=item.external_id,
            occurred_at=item.occurred_at,
            title=item.title,
            normalized_event_type=item.normalized_event_type,
        )
        external_id = (item.external_id or fingerprint).strip()
        return ImportRecord(
            user_id=user_id,
            source_type=source_type,
            source_name=source_name,
            external_id=external_id,
            fingerprint=fingerprint,
            occurred_at=item.occurred_at,
            title=item.title,
            description=item.description or "",
            tags=tags,
            raw_payload=payload,
            normalized_event_type=item.normalized_event_type or "imported:event",
        )

    def _to_event(self, *, user_id: int, record: ImportRecord) -> Event:
        description = record.description or record.title
        return Event(
            user_id=user_id,
            event_type=record.normalized_event_type,
            timestamp=record.occurred_at,
            description=description,
            tags=self.build_event_tags(record),
        )

    @classmethod
    def build_event_tags(cls, record: ImportRecord) -> list[str]:
        tags = [
            "imported",
            f"source:{cls.normalize_source_value(record.source_type)}",
            f"source_name:{cls.normalize_source_value(record.source_name)}",
        ]
        tags.extend(cls.normalize_tags(record.tags))
        deduped = []
        for tag in tags:
            if tag not in deduped:
                deduped.append(tag)
        return deduped

    @staticmethod
    def normalize_source_value(value: str) -> str:
        safe = "".join(char.lower() if char.isalnum() else "-" for char in (value or "").strip())
        while "--" in safe:
            safe = safe.replace("--", "-")
        return safe.strip("-")

    @classmethod
    def normalize_tags(cls, tags: list[str]) -> list[str]:
        normalized = []
        for tag in tags or []:
            clean = str(tag).strip().lower()
            if clean:
                normalized.append(clean)
        return normalized

    @staticmethod
    def build_fingerprint(
        *,
        source_type: str,
        source_name: str,
        external_id: Optional[str],
        occurred_at: datetime,
        title: str,
        normalized_event_type: str,
    ) -> str:
        raw = "|".join(
            [
                source_type,
                source_name,
                (external_id or "").strip(),
                occurred_at.isoformat(),
                (title or "").strip(),
                (normalized_event_type or "").strip(),
            ]
        )
        return hashlib.sha1(raw.encode("utf-8")).hexdigest()
