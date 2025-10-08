import os
from typing import List, Optional
from uuid import uuid4

from gabru.apple.shortcuts import ShortcutBuilder
from gabru.db.db import DB
from gabru.db.service import CRUDService, T
from model.shortcut import Shortcut


class ShortcutService(CRUDService[Shortcut]):
    def __init__(self):
        # Initialize with the table name "shortcuts" and a corresponding DB instance
        super().__init__(
            "shortcuts", DB("rasbhari")
        )
        self.RASBHARI_LOCAL_URL = os.getenv("RASBHARI_LOCAL_URL", "rasbhari.local:5000")
        self.SERVER_FILES_FOLDER = os.getenv("SERVER_FILES_FOLDER", "/tmp")

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

    def create(self, obj: Shortcut) -> Optional[int]:
        new_obj_id = super().create(obj)

        file_name = obj.filename
        filepath = os.path.join(self.SERVER_FILES_FOLDER, file_name)

        builder = ShortcutBuilder(obj.name)
        builder.add_post_request(
            url=f"{self.RASBHARI_LOCAL_URL}/shortcuts/invoke/{new_obj_id}",
            headers={"Content-Type": "application/json"}
        )
        builder.save(filepath=filepath)

        return new_obj_id
