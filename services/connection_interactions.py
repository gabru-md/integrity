from datetime import datetime
from typing import List, Optional

from gabru.db.db import DB
from gabru.db.service import CRUDService
from model.connection_interaction import ConnectionInteraction


class ConnectionInteractionService(CRUDService[ConnectionInteraction]):
    def __init__(self):
        super().__init__("connection_interactions", DB("rasbhari"), user_scoped=True)

    def _create_table(self):
        if self.db.conn:
            with self.db.conn.cursor() as cursor:
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS connection_interactions (
                        id SERIAL PRIMARY KEY,
                        user_id INTEGER NOT NULL,
                        connection_id INTEGER NOT NULL REFERENCES connections(id) ON DELETE CASCADE,
                        connection_name VARCHAR(255) NOT NULL,
                        interaction_type VARCHAR(50) NOT NULL,
                        medium VARCHAR(100) DEFAULT '',
                        duration_minutes INTEGER NOT NULL DEFAULT 0,
                        quality_score INTEGER NOT NULL DEFAULT 3,
                        notes TEXT DEFAULT '',
                        tags TEXT[] DEFAULT ARRAY[]::TEXT[],
                        created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
                    )
                """)
                self.db.conn.commit()

    def _to_tuple(self, entity: ConnectionInteraction) -> tuple:
        return (
            entity.user_id,
            entity.connection_id,
            entity.connection_name,
            entity.interaction_type,
            entity.medium,
            entity.duration_minutes,
            entity.quality_score,
            entity.notes,
            entity.tags or [],
            entity.created_at,
        )

    def _to_object(self, row: tuple) -> ConnectionInteraction:
        return ConnectionInteraction(
            id=row[0],
            user_id=row[1],
            connection_id=row[2],
            connection_name=row[3],
            interaction_type=row[4],
            medium=row[5] or "",
            duration_minutes=row[6] or 0,
            quality_score=row[7] or 3,
            notes=row[8] or "",
            tags=row[9] or [],
            created_at=row[10],
        )

    def _get_columns_for_insert(self) -> List[str]:
        return ["user_id", "connection_id", "connection_name", "interaction_type", "medium", "duration_minutes", "quality_score", "notes", "tags", "created_at"]

    def _get_columns_for_update(self) -> List[str]:
        return self._get_columns_for_insert()

    def _get_columns_for_select(self) -> List[str]:
        return ["id", "user_id", "connection_id", "connection_name", "interaction_type", "medium", "duration_minutes", "quality_score", "notes", "tags", "created_at"]

    def get_by_connection_id(self, connection_id: int, limit: Optional[int] = None) -> List[ConnectionInteraction]:
        interactions = self.find_all(filters={"connection_id": connection_id}, sort_by={"created_at": "DESC"})
        return interactions[:limit] if limit else interactions

    def create(self, obj: ConnectionInteraction) -> Optional[int]:
        created_id = super().create(obj)
        if not created_id:
            return created_id

        try:
            from model.event import Event
            from services.connections import ConnectionService
            from services.events import EventService

            connection_service = ConnectionService()
            event_service = EventService()
            connection = connection_service.get_by_id(obj.connection_id)
            if connection:
                interaction_time = obj.created_at or datetime.now()
                if not connection.last_contact_at or interaction_time > connection.last_contact_at:
                    connection.last_contact_at = interaction_time
                connection_service.update(connection)

            normalized_name = (obj.connection_name or "").strip().lower().replace(" ", "_")
            tags = list(dict.fromkeys([
                "social",
                f"connection:{normalized_name}" if normalized_name else "connection",
                f"interaction:{obj.interaction_type.lower()}",
                *(obj.tags or []),
            ]))

            event_service.create(Event(
                user_id=obj.user_id,
                event_type="connection:interaction_logged",
                timestamp=obj.created_at or datetime.now(),
                description=f"Connected with {obj.connection_name} via {obj.interaction_type}",
                tags=tags
            ))
        except Exception:
            pass

        return created_id

    def update(self, obj: ConnectionInteraction) -> bool:
        updated = super().update(obj)
        if updated:
            self._refresh_connection_last_contact(obj.connection_id)
        return updated

    def delete(self, obj_id: int) -> bool:
        interaction = self.get_by_id(obj_id)
        if not interaction:
            return False

        deleted = super().delete(obj_id)
        if deleted:
            self._refresh_connection_last_contact(interaction.connection_id)
        return deleted

    def _refresh_connection_last_contact(self, connection_id: int):
        try:
            from services.connections import ConnectionService

            connection_service = ConnectionService()
            connection = connection_service.get_by_id(connection_id)
            if not connection:
                return

            interactions = self.get_by_connection_id(connection_id, limit=1)
            connection.last_contact_at = interactions[0].created_at if interactions else None
            connection_service.update(connection)
        except Exception:
            pass
