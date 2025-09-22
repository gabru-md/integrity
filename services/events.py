from model.event import Event
from gabru.service import CRUDService
from gabru.db import DB
from typing import List


class EventService(CRUDService[Event]):
    def __init__(self):
        super().__init__(
            "events", DB("events")
        )

    def _create_table(self):
        if self.db.conn:
            with self.db.conn.cursor() as cursor:
                cursor.execute("""
                            CREATE TABLE IF NOT EXISTS events (
                                id SERIAL PRIMARY KEY,
                                event_type VARCHAR(255) NOT NULL,
                                timestamp BIGINT NOT NULL,
                                description TEXT,
                                tags TEXT[]
                            )
                        """)
                self.db.conn.commit()

    def _to_tuple(self, event: Event) -> tuple:
        return (event.event_type, event.timestamp, event.description, event.tags)

    def _to_object(self, row: tuple) -> Event:
        event_dict = {
            "id": row[0],
            "event_type": row[1],
            "timestamp": row[2],
            "description": row[3],
            "tags": row[4] if row[4] else []
        }
        return Event(**event_dict)

    def _get_columns_for_insert(self) -> List[str]:
        return ["event_type", "timestamp", "description", "tags"]

    def _get_columns_for_update(self) -> List[str]:
        return ["event_type", "timestamp", "description", "tags"]

    def _get_columns_for_select(self) -> List[str]:
        return ["id", "event_type", "timestamp", "description", "tags"]
