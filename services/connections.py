from typing import List, Optional

from gabru.db.db import DB
from gabru.db.service import CRUDService
from model.connection import Connection


class ConnectionService(CRUDService[Connection]):
    def __init__(self):
        super().__init__("connections", DB("rasbhari"))

    def _create_table(self):
        if self.db.conn:
            with self.db.conn.cursor() as cursor:
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS connections (
                        id SERIAL PRIMARY KEY,
                        name VARCHAR(255) NOT NULL UNIQUE,
                        relationship_type VARCHAR(50) NOT NULL,
                        cadence_days INTEGER NOT NULL DEFAULT 14,
                        priority VARCHAR(20) NOT NULL DEFAULT 'Medium',
                        notes TEXT DEFAULT '',
                        tags TEXT[] DEFAULT ARRAY[]::TEXT[],
                        active BOOLEAN NOT NULL DEFAULT TRUE,
                        created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                        last_contact_at TIMESTAMP
                    )
                """)
                self.db.conn.commit()

    def _to_tuple(self, entity: Connection) -> tuple:
        return (
            entity.name,
            entity.relationship_type,
            entity.cadence_days,
            entity.priority,
            entity.notes,
            entity.tags or [],
            entity.active,
            entity.created_at,
            entity.last_contact_at,
        )

    def _to_object(self, row: tuple) -> Connection:
        return Connection(
            id=row[0],
            name=row[1],
            relationship_type=row[2],
            cadence_days=row[3],
            priority=row[4],
            notes=row[5] or "",
            tags=row[6] or [],
            active=row[7],
            created_at=row[8],
            last_contact_at=row[9],
        )

    def _get_columns_for_insert(self) -> List[str]:
        return ["name", "relationship_type", "cadence_days", "priority", "notes", "tags", "active", "created_at", "last_contact_at"]

    def _get_columns_for_update(self) -> List[str]:
        return self._get_columns_for_insert()

    def _get_columns_for_select(self) -> List[str]:
        return ["id", "name", "relationship_type", "cadence_days", "priority", "notes", "tags", "active", "created_at", "last_contact_at"]

    def get_by_name(self, name: str) -> Optional[Connection]:
        return self.find_one_by_field("name", name)

    def get_active(self) -> List[Connection]:
        return self.find_all(filters={"active": True}, sort_by={"last_contact_at": "ASC"})
