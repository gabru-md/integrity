from datetime import datetime
from model.promise import Promise
from gabru.db.service import CRUDService
from gabru.db.db import DB
from typing import List, Optional


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
                self.db.conn.commit()

    def get_due_promises(self) -> List[Promise]:
        """Finds all promises that need checking (next_check_at <= now)."""
        filters = {
            "next_check_at": {"$lt": datetime.now()},
            "status": "active"
        }
        return self.find_all(filters=filters)

    def get_promises_by_status(self, status: str) -> List[Promise]:
        return self.find_all(filters={"status": status})

    def _to_tuple(self, promise: Promise) -> tuple:
        return (
            promise.user_id, promise.name, promise.description, promise.frequency,
            promise.target_event_tag, promise.target_event_type, promise.required_count,
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
            "target_event_type": row[6],
            "required_count": row[7],
            "is_negative": row[8],
            "max_allowed": row[9],
            "status": row[10],
            "current_count": row[11],
            "streak": row[12],
            "best_streak": row[13],
            "total_completions": row[14],
            "total_periods": row[15],
            "last_checked_at": row[16],
            "next_check_at": row[17],
            "created_at": row[18],
            "updated_at": row[19]
        }
        return Promise(**promise_dict)

    def _get_columns_for_insert(self) -> List[str]:
        return ["user_id", "name", "description", "frequency", "target_event_tag", "target_event_type", 
                "required_count", "is_negative", "max_allowed", "status", "current_count", "streak", 
                "best_streak", "total_completions", "total_periods", "last_checked_at", "next_check_at", 
                "created_at", "updated_at"]

    def _get_columns_for_update(self) -> List[str]:
        return self._get_columns_for_insert()

    def _get_columns_for_select(self) -> List[str]:
        return ["id", "user_id", "name", "description", "frequency", "target_event_tag", "target_event_type", 
                "required_count", "is_negative", "max_allowed", "status", "current_count", "streak", 
                "best_streak", "total_completions", "total_periods", "last_checked_at", "next_check_at", 
                "created_at", "updated_at"]
