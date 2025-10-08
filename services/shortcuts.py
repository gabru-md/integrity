from typing import List

from gabru.db.db import DB
from gabru.db.service import CRUDService
from model.shortcut import Shortcut


class ShortcutService(CRUDService[Shortcut]):
    def __init__(self):
        # Initialize with the table name "shortcuts" and a corresponding DB instance
        super().__init__(
            "shortcuts", DB("rasbhari")
        )

    def _create_table(self):
        if self.db.conn:
            with self.db.conn.cursor() as cursor:
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS shortcuts (
                        id SERIAL PRIMARY KEY,
                        name VARCHAR(255) NOT NULL,
                        event_type VARCHAR(255) NOT NULL,
                        description VARCHAR(500) NOT NULL,
                        filename VARCHAR(255)
                    )
                """)
                self.db.conn.commit()

    def _to_tuple(self, shortcut: Shortcut) -> tuple:
        return (
            shortcut.name,
            shortcut.event_type,
            shortcut.description,
            shortcut.filename
        )

    def _to_object(self, row: tuple) -> Shortcut:
        """
        Converts a database row (tuple) into a Shortcut object.
        """
        shortcut_dict = {
            "id": row[0],
            "name": row[1],
            "event_type": row[2],
            "description": row[3],
            "filename": row[4]
        }
        return Shortcut(**shortcut_dict)

    def _get_columns_for_insert(self) -> List[str]:
        return ["name", "event_type", "description", "filename"]

    def _get_columns_for_update(self) -> List[str]:
        return ["name", "description"]

    def _get_columns_for_select(self) -> List[str]:
        return ["id", "name", "event_type", "description", "filename"]
