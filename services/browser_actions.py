from typing import List

from gabru.db.db import DB
from gabru.db.service import CRUDService
from model.browser_action import BrowserAction


class BrowserActionService(CRUDService[BrowserAction]):
    def __init__(self):
        super().__init__("browser_actions", DB("rasbhari"), user_scoped=True)

    def _create_table(self):
        if self.db.conn:
            with self.db.conn.cursor() as cursor:
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS browser_actions (
                        id SERIAL PRIMARY KEY,
                        user_id INTEGER NOT NULL,
                        name VARCHAR(255) NOT NULL,
                        browser_action VARCHAR(64) NOT NULL,
                        target_type VARCHAR(64) NOT NULL,
                        description TEXT,
                        target_activity_id INTEGER,
                        target_project_id INTEGER,
                        target_event_type VARCHAR(255),
                        target_tags TEXT[],
                        target_description TEXT,
                        default_payload JSONB NOT NULL DEFAULT '{}'::jsonb,
                        enabled BOOLEAN NOT NULL DEFAULT TRUE,
                        UNIQUE(user_id, name)
                    )
                """)
                cursor.execute("ALTER TABLE browser_actions ADD COLUMN IF NOT EXISTS target_activity_id INTEGER")
                cursor.execute("ALTER TABLE browser_actions ADD COLUMN IF NOT EXISTS target_project_id INTEGER")
                cursor.execute("ALTER TABLE browser_actions ADD COLUMN IF NOT EXISTS target_event_type VARCHAR(255)")
                cursor.execute("ALTER TABLE browser_actions ADD COLUMN IF NOT EXISTS target_tags TEXT[]")
                cursor.execute("ALTER TABLE browser_actions ADD COLUMN IF NOT EXISTS target_description TEXT")
                cursor.execute("ALTER TABLE browser_actions ADD COLUMN IF NOT EXISTS default_payload JSONB NOT NULL DEFAULT '{}'::jsonb")
                cursor.execute("ALTER TABLE browser_actions ADD COLUMN IF NOT EXISTS enabled BOOLEAN NOT NULL DEFAULT TRUE")
                self.db.conn.commit()

    def _to_tuple(self, action: BrowserAction) -> tuple:
        return (
            action.user_id,
            action.name,
            action.browser_action,
            action.target_type,
            action.description,
            action.target_activity_id,
            action.target_project_id,
            action.target_event_type,
            action.target_tags,
            action.target_description,
            action.default_payload or {},
            action.enabled,
        )

    def _to_object(self, row: tuple) -> BrowserAction:
        return BrowserAction(
            id=row[0],
            user_id=row[1],
            name=row[2],
            browser_action=row[3],
            target_type=row[4],
            description=row[5],
            target_activity_id=row[6],
            target_project_id=row[7],
            target_event_type=row[8],
            target_tags=row[9] or [],
            target_description=row[10],
            default_payload=row[11] or {},
            enabled=row[12],
        )

    def _get_columns_for_insert(self) -> List[str]:
        return [
            "user_id",
            "name",
            "browser_action",
            "target_type",
            "description",
            "target_activity_id",
            "target_project_id",
            "target_event_type",
            "target_tags",
            "target_description",
            "default_payload",
            "enabled",
        ]

    def _get_columns_for_update(self) -> List[str]:
        return self._get_columns_for_insert()

    def _get_columns_for_select(self) -> List[str]:
        return [
            "id",
            "user_id",
            "name",
            "browser_action",
            "target_type",
            "description",
            "target_activity_id",
            "target_project_id",
            "target_event_type",
            "target_tags",
            "target_description",
            "default_payload",
            "enabled",
        ]
