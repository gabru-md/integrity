from datetime import datetime

from model.event import Event
from gabru.db.service import CRUDService
from gabru.db.db import DB
from typing import List, Optional


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
                                timestamp TIMESTAMP NOT NULL,
                                description TEXT,
                                tags TEXT[]
                            ) PARTITION BY RANGE (timestamp)
                        """)
                self.db.conn.commit()

    def find_by_event_type_and_time_range(self, event_types: List[str], max_timestamp: int, min_timestamp: int) -> List[
        Event]:
        """Finds all events of the specified types within a given time range."""
        filters = {
            "event_type": {"$in": event_types},
            "timestamp": {"$lt": datetime.fromtimestamp(max_timestamp), "$gt": datetime.fromtimestamp(min_timestamp)}
        }
        sort_by = {"timestamp": "ASC"}
        return self.find_all(filters=filters, sort_by=sort_by)

    def find_latest_event_before(self, event_type: str, max_timestamp: int) -> Optional[Event]:
        """
        Finds the single latest event of a specific type that occurred strictly before max_timestamp.
        This is optimized for the 'SINCE' logic.

        NOTE: Assuming the timestamp is stored as an integer epoch time or is handled appropriately
              by the underlying database layer when compared to the integer max_timestamp.
        """
        try:
            with self.db.conn.cursor() as cursor:
                # Selects the most recent event (DESC) of the given type that is older than max_timestamp (the trigger time)
                query = """
                    SELECT * FROM events
                    WHERE event_type = %s AND timestamp < %s
                    ORDER BY timestamp DESC
                    LIMIT 1
                """
                cursor.execute(query, (event_type, max_timestamp))
                row = cursor.fetchone()

                if row:
                    return self._to_object(row)
                return None
        except Exception as e:
            # self.log.error(f"Error finding latest event: {e}")
            return None

    def _to_tuple(self, event: Event) -> tuple:
        return (
            event.event_type, event.timestamp, event.description, event.tags)

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
