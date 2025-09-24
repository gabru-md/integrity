from typing import List

from gabru.db.db import DB
from gabru.db.service import CRUDService
from gabru.qprocessor.qstats import QueueStats


class QueueService(CRUDService[QueueStats]):
    def __init__(self):
        super().__init__("queuestats", DB("queue"))

    def _create_table(self):
        if self.db.get_conn():
            with self.db.get_conn() as cursor:
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS queuestats (
                        name VARCHAR(255) PRIMARY KEY,
                        last_consumed_id INT
                    )
                """)
                self.db.conn.commit()

    def _to_tuple(self, qstats: QueueStats) -> tuple:
        return (
            qstats.name, qstats.last_consumed_id)

    def _to_object(self, row: tuple) -> QueueStats:
        qstat_dict = {
            "name": row[0],
            "last_consumed_id": row[1]
        }
        return QueueStats(**qstat_dict)

    def _get_columns_for_insert(self) -> List[str]:
        return ["name", "last_consumed_id"]

    def _get_columns_for_update(self) -> List[str]:
        return ["name", "last_consumed_id"]

    def _get_columns_for_select(self) -> List[str]:
        return ["name", "last_consumed_id"]
