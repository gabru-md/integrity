from __future__ import annotations

import json
from datetime import datetime
from typing import List, Optional

from gabru.db.db import DB
from gabru.db.service import CRUDService
from model.import_record import ImportRecord


class ImportRecordService(CRUDService[ImportRecord]):
    def __init__(self):
        super().__init__("import_records", DB("rasbhari"), user_scoped=True)

    def _create_table(self):
        if self.db.conn:
            with self.db.conn.cursor() as cursor:
                cursor.execute(
                    """
                    CREATE TABLE IF NOT EXISTS import_records (
                        id SERIAL PRIMARY KEY,
                        user_id INTEGER NOT NULL,
                        source_type VARCHAR(100) NOT NULL,
                        source_name VARCHAR(255) NOT NULL,
                        external_id VARCHAR(255) NOT NULL,
                        fingerprint VARCHAR(255) NOT NULL,
                        occurred_at TIMESTAMP NOT NULL,
                        title VARCHAR(255) NOT NULL,
                        description TEXT,
                        tags TEXT[] DEFAULT ARRAY[]::TEXT[],
                        raw_payload TEXT DEFAULT '{}',
                        normalized_event_type VARCHAR(255) NOT NULL,
                        imported_event_id BIGINT,
                        created_at TIMESTAMP NOT NULL DEFAULT NOW()
                    )
                    """
                )
                cursor.execute(
                    """
                    CREATE UNIQUE INDEX IF NOT EXISTS idx_import_records_source_key
                    ON import_records(user_id, source_type, source_name, external_id)
                    """
                )
                cursor.execute(
                    """
                    CREATE UNIQUE INDEX IF NOT EXISTS idx_import_records_fingerprint
                    ON import_records(user_id, source_type, source_name, fingerprint)
                    """
                )
                self.db.conn.commit()

    def _to_tuple(self, entity: ImportRecord) -> tuple:
        return (
            entity.user_id,
            entity.source_type,
            entity.source_name,
            entity.external_id,
            entity.fingerprint,
            entity.occurred_at,
            entity.title,
            entity.description,
            entity.tags,
            json.dumps(entity.raw_payload or {}, ensure_ascii=True),
            entity.normalized_event_type,
            entity.imported_event_id,
            entity.created_at,
        )

    def _to_object(self, row: tuple) -> ImportRecord:
        return ImportRecord(
            id=row[0],
            user_id=row[1],
            source_type=row[2],
            source_name=row[3],
            external_id=row[4],
            fingerprint=row[5],
            occurred_at=row[6],
            title=row[7],
            description=row[8] or "",
            tags=row[9] or [],
            raw_payload=json.loads(row[10] or "{}"),
            normalized_event_type=row[11],
            imported_event_id=row[12],
            created_at=row[13] or datetime.now(),
        )

    def _get_columns_for_insert(self) -> List[str]:
        return [
            "user_id",
            "source_type",
            "source_name",
            "external_id",
            "fingerprint",
            "occurred_at",
            "title",
            "description",
            "tags",
            "raw_payload",
            "normalized_event_type",
            "imported_event_id",
            "created_at",
        ]

    def _get_columns_for_update(self) -> List[str]:
        return self._get_columns_for_insert()

    def _get_columns_for_select(self) -> List[str]:
        return [
            "id",
            "user_id",
            "source_type",
            "source_name",
            "external_id",
            "fingerprint",
            "occurred_at",
            "title",
            "description",
            "tags",
            "raw_payload",
            "normalized_event_type",
            "imported_event_id",
            "created_at",
        ]

    def get_by_source_key(
        self,
        *,
        user_id: int,
        source_type: str,
        source_name: str,
        external_id: str,
    ) -> Optional[ImportRecord]:
        records = self.find_all(
            filters={
                "user_id": user_id,
                "source_type": source_type,
                "source_name": source_name,
                "external_id": external_id,
            }
        )
        return records[0] if records else None

    def get_by_fingerprint(
        self,
        *,
        user_id: int,
        source_type: str,
        source_name: str,
        fingerprint: str,
    ) -> Optional[ImportRecord]:
        records = self.find_all(
            filters={
                "user_id": user_id,
                "source_type": source_type,
                "source_name": source_name,
                "fingerprint": fingerprint,
            }
        )
        return records[0] if records else None
