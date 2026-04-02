from typing import List

from gabru.db.db import DB
from gabru.db.service import CRUDService
from gabru.qprocessor.qstats import QueueStats


class QueueService(CRUDService[QueueStats]):
    def __init__(self):
        super().__init__("queuestats", DB("queue"))

    def _create_table(self):
        if self.db.conn:
            with self.db.conn.cursor() as cursor:
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS queuestats (
                        id SERIAL PRIMARY KEY,
                        name VARCHAR(255) UNIQUE NOT NULL,
                        last_consumed_id INT
                    )
                """)
                self.db.conn.commit()

    def _to_tuple(self, qstats: QueueStats) -> tuple:
        return (
            qstats.name, qstats.last_consumed_id)

    def _to_object(self, row: tuple) -> QueueStats:
        qstat_dict = {
            "id": row[0],
            "name": row[1],
            "last_consumed_id": row[2]
        }
        return QueueStats(**qstat_dict)

    def _get_columns_for_insert(self) -> List[str]:
        return ["name", "last_consumed_id"]

    def _get_columns_for_update(self) -> List[str]:
        return ["name", "last_consumed_id"]

    def _get_columns_for_select(self) -> List[str]:
        return ["id", "name", "last_consumed_id"]

    def set_last_consumed_id(self, process_name: str, last_consumed_id: int) -> QueueStats:
        existing = self.find_one_by_field("name", process_name)
        if existing:
            existing.last_consumed_id = last_consumed_id
            self.update(existing)
            return self.find_one_by_field("name", process_name) or existing

        created = QueueStats(name=process_name, last_consumed_id=last_consumed_id)
        created_id = self.create(created)
        if created_id:
            fresh = self.get_by_id(created_id)
            if fresh:
                return fresh
        return created
