from typing import List

from gabru.db.db import DB
from gabru.db.service import CRUDService
from model.skill_level_history import SkillLevelHistory


class SkillLevelHistoryService(CRUDService[SkillLevelHistory]):
    def __init__(self):
        super().__init__("skill_level_history", DB("rasbhari"))

    def _create_table(self):
        if self.db.conn:
            with self.db.conn.cursor() as cursor:
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS skill_level_history (
                        id SERIAL PRIMARY KEY,
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
            skill_id=row[1],
            skill_name=row[2],
            level=row[3],
            total_xp=row[4],
            reached_at=row[5],
            summary=row[6],
        )

    def _get_columns_for_insert(self) -> List[str]:
        return ["skill_id", "skill_name", "level", "total_xp", "reached_at", "summary"]

    def _get_columns_for_update(self) -> List[str]:
        return ["skill_id", "skill_name", "level", "total_xp", "reached_at", "summary"]

    def _get_columns_for_select(self) -> List[str]:
        return ["id", "skill_id", "skill_name", "level", "total_xp", "reached_at", "summary"]

    def get_recent_history(self, limit: int = 10) -> List[SkillLevelHistory]:
        if not self.db.get_conn():
            return []

        columns = ", ".join(self._get_columns_for_select())
        query = f"SELECT {columns} FROM {self.table_name} ORDER BY reached_at DESC LIMIT %s"
        with self.db.get_conn().cursor() as cursor:
            cursor.execute(query, (limit,))
            return [self._to_object(row) for row in cursor.fetchall()]
