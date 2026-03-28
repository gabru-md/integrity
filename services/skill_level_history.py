from typing import List

from gabru.db.db import DB
from gabru.db.service import CRUDService
from model.skill_level_history import SkillLevelHistory


class SkillLevelHistoryService(CRUDService[SkillLevelHistory]):
    def __init__(self):
        super().__init__("skill_level_history", DB("rasbhari"), user_scoped=True)

    def _create_table(self):
        if self.db.conn:
            with self.db.conn.cursor() as cursor:
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS skill_level_history (
                        id SERIAL PRIMARY KEY,
                        user_id INTEGER NOT NULL,
                        skill_id INTEGER NOT NULL REFERENCES skills(id) ON DELETE CASCADE,
                        skill_name VARCHAR(255) NOT NULL,
                        level INTEGER NOT NULL,
                        total_xp INTEGER NOT NULL,
                        reached_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                        summary TEXT NOT NULL
                    )
                """)
                self.db.conn.commit()

    def _to_tuple(self, entity: SkillLevelHistory) -> tuple:
        return (
            entity.user_id,
            entity.skill_id,
            entity.skill_name,
            entity.level,
            entity.total_xp,
            entity.reached_at,
            entity.summary,
        )

    def _to_object(self, row: tuple) -> SkillLevelHistory:
        return SkillLevelHistory(
            id=row[0],
            user_id=row[1],
            skill_id=row[2],
            skill_name=row[3],
            level=row[4],
            total_xp=row[5],
            reached_at=row[6],
            summary=row[7],
        )

    def _get_columns_for_insert(self) -> List[str]:
        return ["user_id", "skill_id", "skill_name", "level", "total_xp", "reached_at", "summary"]

    def _get_columns_for_update(self) -> List[str]:
        return ["user_id", "skill_id", "skill_name", "level", "total_xp", "reached_at", "summary"]

    def _get_columns_for_select(self) -> List[str]:
        return ["id", "user_id", "skill_id", "skill_name", "level", "total_xp", "reached_at", "summary"]

    def get_recent_history(self, limit: int = 10) -> List[SkillLevelHistory]:
        return self.find_all(sort_by={"reached_at": "DESC"})[:limit]
