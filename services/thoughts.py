from typing import List, Optional
from datetime import datetime

from gabru.eventing import emit_event_safely
from gabru.db.db import DB
from gabru.db.service import CRUDService
from model.thought import Thought


class ThoughtService(CRUDService[Thought]):
    def __init__(self):
        super().__init__(
            "thoughts", DB("thoughts"), user_scoped=True
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
                        user_id INTEGER NOT NULL,
                        message VARCHAR(500) NOT NULL,
                        created_at TIMESTAMP WITHOUT TIME ZONE
                    )
                """)
                self.db.conn.commit()

    def _to_tuple(self, thought: Thought) -> tuple:
        created_at = thought.created_at if thought.created_at else datetime.now()

        return (
            thought.user_id,
            thought.message,
            created_at,
        )

    def _to_object(self, row: tuple) -> Thought:
        thought_dict = {
            "id": row[0],
            "user_id": row[1],
            "message": row[2],
            "created_at": row[3]
        }
        return Thought(**thought_dict)

    def _get_columns_for_insert(self) -> List[str]:
        return ["user_id", "message", "created_at"]

    def _get_columns_for_update(self) -> List[str]:
        return ["user_id", "message", "created_at"]

    def _get_columns_for_select(self) -> List[str]:
        return ["id", "user_id", "message", "created_at"]

    def create(self, obj: Thought) -> Optional[int]:
        res = super().create(obj)
        if res:
            emit_event_safely(
                self.log,
                user_id=obj.user_id,
                event_type="thought:posted",
                timestamp=datetime.now(),
                description="New thought posted",
                tags=["thought"],
            )
        return res
