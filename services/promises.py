from datetime import datetime
from model.promise import Promise
from gabru.db.service import CRUDService
from gabru.db.db import DB
from typing import List, Optional
import json


class PromiseService(CRUDService[Promise]):
    def __init__(self):
        super().__init__(
            "promises", DB("rasbhari"), user_scoped=True
        )

    def _create_table(self):
        if self.db.conn:
            with self.db.conn.cursor() as cursor:
                cursor.execute("""
                            CREATE TABLE IF NOT EXISTS promises (
                                id SERIAL PRIMARY KEY,
                                user_id INTEGER NOT NULL,
                                name VARCHAR(255) NOT NULL,
                                description TEXT,
                                frequency VARCHAR(50) NOT NULL,
                                target_event_tag VARCHAR(255),
                                target_event_type VARCHAR(255),
                                required_count INTEGER DEFAULT 1,
                                is_negative BOOLEAN DEFAULT FALSE,
                                max_allowed INTEGER DEFAULT 0,
                                status VARCHAR(50) DEFAULT 'active',
                                current_count INTEGER DEFAULT 0,
                                streak INTEGER DEFAULT 0,
                                best_streak INTEGER DEFAULT 0,
                                total_completions INTEGER DEFAULT 0,
                                total_periods INTEGER DEFAULT 0,
                                last_checked_at TIMESTAMP,
                                next_check_at TIMESTAMP,
                                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                            )
                        """)
                cursor.execute("ALTER TABLE promises ADD COLUMN IF NOT EXISTS target_event_tags TEXT")
                cursor.execute("ALTER TABLE promises ADD COLUMN IF NOT EXISTS target_event_tags_match_mode VARCHAR(10) DEFAULT 'any'")
                self.db.conn.commit()

    def get_due_promises(self) -> List[Promise]:
        """Finds all promises that need checking (next_check_at <= now)."""
        filters = {
            "next_check_at": {"$lt": datetime.now()},
        }
        due_promises = self.find_all(filters=filters)
        return [
            promise for promise in due_promises
            if promise.frequency != "once" or promise.status == "active"
        ]

    def get_promises_by_status(self, status: str) -> List[Promise]:
        return self.find_all(filters={"status": status})

    def _to_tuple(self, promise: Promise) -> tuple:
        tags = self._normalize_tags(promise.target_event_tags, promise.target_event_tag)
        return (
            promise.user_id, promise.name, promise.description, promise.frequency,
            promise.target_event_tag, json.dumps(tags), promise.target_event_tags_match_mode,
            promise.target_event_type, promise.required_count,
            promise.is_negative, promise.max_allowed,
            promise.status, promise.current_count, promise.streak, promise.best_streak,
            promise.total_completions, promise.total_periods,
            promise.last_checked_at, promise.next_check_at,
            promise.created_at, promise.updated_at
        )

    def _to_object(self, row: tuple) -> Promise:
        promise_dict = {
            "id": row[0],
            "user_id": row[1],
            "name": row[2],
            "description": row[3],
            "frequency": row[4],
            "target_event_tag": row[5],
            "target_event_tags": self._decode_tags(row[6]),
            "target_event_tags_match_mode": row[7] or "any",
            "target_event_type": row[8],
            "required_count": row[9],
            "is_negative": row[10],
            "max_allowed": row[11],
            "status": row[12],
            "current_count": row[13],
            "streak": row[14],
            "best_streak": row[15],
            "total_completions": row[16],
            "total_periods": row[17],
            "last_checked_at": row[18],
            "next_check_at": row[19],
            "created_at": row[20],
            "updated_at": row[21]
        }
        return Promise(**promise_dict)

    @staticmethod
    def _normalize_tags(tags: Optional[List[str]], legacy_tag: Optional[str] = None) -> List[str]:
        normalized: List[str] = []
        if legacy_tag and str(legacy_tag).strip():
            normalized.append(str(legacy_tag).strip())
        for tag in tags or []:
            value = str(tag).strip()
            if value and value not in normalized:
                normalized.append(value)
        return normalized

    @staticmethod
    def _decode_tags(value) -> List[str]:
        if not value:
            return []
        if isinstance(value, list):
            return [str(tag).strip() for tag in value if str(tag).strip()]
        if isinstance(value, str):
            try:
                parsed = json.loads(value)
            except Exception:
                parsed = [part.strip() for part in value.split(",")]
            if isinstance(parsed, list):
                return [str(tag).strip() for tag in parsed if str(tag).strip()]
        return []

    def _get_columns_for_insert(self) -> List[str]:
        return ["user_id", "name", "description", "frequency", "target_event_tag", "target_event_tags",
                "target_event_tags_match_mode", "target_event_type", "required_count", "is_negative", "max_allowed",
                "status", "current_count", "streak", "best_streak", "total_completions", "total_periods",
                "last_checked_at", "next_check_at", "created_at", "updated_at"]

    def _get_columns_for_update(self) -> List[str]:
        return self._get_columns_for_insert()

    def _get_columns_for_select(self) -> List[str]:
        return ["id", "user_id", "name", "description", "frequency", "target_event_tag", "target_event_tags",
                "target_event_tags_match_mode", "target_event_type", "required_count", "is_negative", "max_allowed",
                "status", "current_count", "streak", "best_streak", "total_completions", "total_periods",
                "last_checked_at", "next_check_at", "created_at", "updated_at"]
