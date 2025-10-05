from typing import List
from datetime import datetime

from gabru.db.db import DB
from gabru.db.service import CRUDService
from model.thought import Thought


class ThoughtService(CRUDService[Thought]):
    def __init__(self):
        super().__init__(
            "thoughts", DB("thoughts")
        )

    def _create_table(self):
        """
        Initializes the 'thoughts' table in the database.
        """
        if self.db.conn:
            with self.db.conn.cursor() as cursor:
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS thoughts (
                        id SERIAL PRIMARY KEY,
                        message VARCHAR(500) NOT NULL,
                        created_at TIMESTAMP WITHOUT TIME ZONE
                    )
                """)
                self.db.conn.commit()

    def _to_tuple(self, thought: Thought) -> tuple:
        created_at = thought.created_at if thought.created_at else datetime.now()

        return (
            thought.message,
            created_at,
        )

    def _to_object(self, row: tuple) -> Thought:
        thought_dict = {
            "id": row[0],
            "message": row[1],
            "created_at": row[2]
        }
        return Thought(**thought_dict)

    def _get_columns_for_insert(self) -> List[str]:
        return ["message", "created_at"]

    def _get_columns_for_update(self) -> List[str]:
        return ["message"]

    def _get_columns_for_select(self) -> List[str]:
        return ["id", "message", "created_at"]
