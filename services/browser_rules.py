from typing import List

from gabru.db.db import DB
from gabru.db.service import CRUDService
from model.browser_rule import BrowserRule


class BrowserRuleService(CRUDService[BrowserRule]):
    def __init__(self):
        super().__init__("browser_rules", DB("rasbhari"), user_scoped=True)

    def _create_table(self):
        if self.db.conn:
            with self.db.conn.cursor() as cursor:
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS browser_rules (
                        id SERIAL PRIMARY KEY,
                        user_id INTEGER NOT NULL,
                        name VARCHAR(255) NOT NULL,
                        browser_action_id INTEGER,
                        trigger_mode VARCHAR(32) NOT NULL,
                        condition_type VARCHAR(64) NOT NULL,
                        active_duration_seconds INTEGER,
                        domain_equals VARCHAR(255),
                        domain_suffix VARCHAR(255),
                        domain_in TEXT[],
                        url_contains TEXT,
                        url_prefix TEXT,
                        selection_required BOOLEAN NOT NULL DEFAULT FALSE,
                        payload_behavior VARCHAR(64) NOT NULL DEFAULT 'merge_browser_context',
                        payload_mapping JSONB NOT NULL DEFAULT '{}'::jsonb,
                        priority INTEGER NOT NULL DEFAULT 100,
                        enabled BOOLEAN NOT NULL DEFAULT TRUE
                    )
                """)
                cursor.execute("ALTER TABLE browser_rules ADD COLUMN IF NOT EXISTS browser_action_id INTEGER")
                cursor.execute("ALTER TABLE browser_rules ADD COLUMN IF NOT EXISTS trigger_mode VARCHAR(32) NOT NULL DEFAULT 'confirm'")
                cursor.execute("ALTER TABLE browser_rules ADD COLUMN IF NOT EXISTS condition_type VARCHAR(64) NOT NULL DEFAULT 'popup_action'")
                cursor.execute("ALTER TABLE browser_rules ADD COLUMN IF NOT EXISTS active_duration_seconds INTEGER")
                cursor.execute("ALTER TABLE browser_rules ADD COLUMN IF NOT EXISTS domain_equals VARCHAR(255)")
                cursor.execute("ALTER TABLE browser_rules ADD COLUMN IF NOT EXISTS domain_suffix VARCHAR(255)")
                cursor.execute("ALTER TABLE browser_rules ADD COLUMN IF NOT EXISTS domain_in TEXT[]")
                cursor.execute("ALTER TABLE browser_rules ADD COLUMN IF NOT EXISTS url_contains TEXT")
                cursor.execute("ALTER TABLE browser_rules ADD COLUMN IF NOT EXISTS url_prefix TEXT")
                cursor.execute("ALTER TABLE browser_rules ADD COLUMN IF NOT EXISTS selection_required BOOLEAN NOT NULL DEFAULT FALSE")
                cursor.execute("ALTER TABLE browser_rules ADD COLUMN IF NOT EXISTS payload_behavior VARCHAR(64) NOT NULL DEFAULT 'merge_browser_context'")
                cursor.execute("ALTER TABLE browser_rules ADD COLUMN IF NOT EXISTS payload_mapping JSONB NOT NULL DEFAULT '{}'::jsonb")
                cursor.execute("ALTER TABLE browser_rules ADD COLUMN IF NOT EXISTS priority INTEGER NOT NULL DEFAULT 100")
                cursor.execute("ALTER TABLE browser_rules ADD COLUMN IF NOT EXISTS enabled BOOLEAN NOT NULL DEFAULT TRUE")
                self.db.conn.commit()

    def _to_tuple(self, rule: BrowserRule) -> tuple:
        return (
            rule.user_id,
            rule.name,
            rule.browser_action_id,
            rule.trigger_mode,
            rule.condition_type,
            rule.active_duration_seconds,
            rule.domain_equals,
            rule.domain_suffix,
            rule.domain_in,
            rule.url_contains,
            rule.url_prefix,
            rule.selection_required,
            rule.payload_behavior,
            rule.payload_mapping or {},
            rule.priority,
            rule.enabled,
        )

    def _to_object(self, row: tuple) -> BrowserRule:
        return BrowserRule(
            id=row[0],
            user_id=row[1],
            name=row[2],
            browser_action_id=row[3],
            trigger_mode=row[4],
            condition_type=row[5],
            active_duration_seconds=row[6],
            domain_equals=row[7],
            domain_suffix=row[8],
            domain_in=row[9] or [],
            url_contains=row[10],
            url_prefix=row[11],
            selection_required=row[12],
            payload_behavior=row[13],
            payload_mapping=row[14] or {},
            priority=row[15],
            enabled=row[16],
        )

    def _get_columns_for_insert(self) -> List[str]:
        return [
            "user_id",
            "name",
            "browser_action_id",
            "trigger_mode",
            "condition_type",
            "active_duration_seconds",
            "domain_equals",
            "domain_suffix",
            "domain_in",
            "url_contains",
            "url_prefix",
            "selection_required",
            "payload_behavior",
            "payload_mapping",
            "priority",
            "enabled",
        ]

    def _get_columns_for_update(self) -> List[str]:
        return self._get_columns_for_insert()

    def _get_columns_for_select(self) -> List[str]:
        return [
            "id",
            "user_id",
            "name",
            "browser_action_id",
            "trigger_mode",
            "condition_type",
            "active_duration_seconds",
            "domain_equals",
            "domain_suffix",
            "domain_in",
            "url_contains",
            "url_prefix",
            "selection_required",
            "payload_behavior",
            "payload_mapping",
            "priority",
            "enabled",
        ]
