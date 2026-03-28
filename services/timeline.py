from typing import List, Optional
from gabru.db.db import DB
from gabru.db.service import CRUDService
from model.timeline import TimelineItem


class TimelineService(CRUDService[TimelineItem]):
    def __init__(self):
        super().__init__("timeline_items", DB("rasbhari"), user_scoped=True)
        self._create_table()

    def _create_table(self):
        if self.db.conn:
            with self.db.conn.cursor() as cursor:
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS timeline_items (
                        id SERIAL PRIMARY KEY,
                        user_id INTEGER NOT NULL,
                        project_id INTEGER NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
                        content TEXT NOT NULL,
                        timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        item_type VARCHAR(50) DEFAULT 'Update'
                    )
                """)
                self.db.conn.commit()

    def _to_tuple(self, entity: TimelineItem) -> tuple:
        return (
            entity.user_id, entity.project_id, entity.content, entity.timestamp, entity.item_type
        )

    def _to_object(self, row: tuple) -> TimelineItem:
        return TimelineItem(
            id=row[0], user_id=row[1], project_id=row[2], content=row[3],
            timestamp=row[4], item_type=row[5]
        )

    def _get_columns_for_insert(self) -> List[str]:
        return ["user_id", "project_id", "content", "timestamp", "item_type"]

    def _get_columns_for_update(self) -> List[str]:
        # Usually updates change content but not project_id or timestamp (unless editing history)
        return ["user_id", "project_id", "content", "timestamp", "item_type"]

    def _get_columns_for_select(self) -> List[str]:
        return ["id", "user_id", "project_id", "content", "timestamp", "item_type"]

    def get_by_project_id(self, project_id: int) -> List[TimelineItem]:
        return self.find_all(filters={"project_id": project_id}, sort_by={"timestamp": "DESC"})
