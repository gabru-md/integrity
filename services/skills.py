from typing import List, Optional

from gabru.db.db import DB
from gabru.db.service import CRUDService
from model.skill import Skill


class SkillService(CRUDService[Skill]):
    def __init__(self):
        super().__init__("skills", DB("rasbhari"))

    def _create_table(self):
        if self.db.conn:
            with self.db.conn.cursor() as cursor:
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS skills (
                        id SERIAL PRIMARY KEY,
                        name VARCHAR(255) NOT NULL UNIQUE,
                        level INTEGER NOT NULL DEFAULT 1,
                        total_xp INTEGER NOT NULL DEFAULT 0,
                        requirement TEXT DEFAULT ''
                    )
                """)
                self.db.conn.commit()

    def _to_tuple(self, entity: Skill) -> tuple:
        return entity.name, entity.level, entity.total_xp, entity.requirement

    def _to_object(self, row: tuple) -> Skill:
        return Skill(
            id=row[0],
            name=row[1],
            level=row[2],
            total_xp=row[3],
            requirement=row[4] or ""
        )

    def _get_columns_for_insert(self) -> List[str]:
        return ["name", "level", "total_xp", "requirement"]

    def _get_columns_for_update(self) -> List[str]:
        return ["name", "level", "total_xp", "requirement"]

    def _get_columns_for_select(self) -> List[str]:
        return ["id", "name", "level", "total_xp", "requirement"]

    def get_by_name(self, name: str) -> Optional[Skill]:
        return self.find_one_by_field("name", name)

    @staticmethod
    def normalize_skill_tag(value: str) -> str:
        return value.strip().lower().lstrip("#")

    @staticmethod
    def xp_floor_for_level(level: int) -> int:
        safe_level = max(1, level)
        return sum(current_level * 100 for current_level in range(1, safe_level))

    @classmethod
    def derive_level(cls, total_xp: int) -> int:
        safe_total_xp = max(0, total_xp)
        level = 1
        remaining_xp = safe_total_xp

        while remaining_xp >= level * 100:
            remaining_xp -= level * 100
            level += 1

        return level

    @classmethod
    def get_progress_snapshot(cls, skill: Skill) -> dict:
        level = max(1, cls.derive_level(skill.total_xp))
        xp_floor = cls.xp_floor_for_level(level)
        xp_into_level = max(0, skill.total_xp - xp_floor)
        xp_for_next_level = level * 100
        progress_percent = int((xp_into_level / xp_for_next_level) * 100) if xp_for_next_level else 100

        return {
            "id": skill.id,
            "name": skill.name,
            "level": level,
            "total_xp": skill.total_xp,
            "requirement": skill.requirement,
            "xp_into_level": xp_into_level,
            "xp_for_next_level": xp_for_next_level,
            "progress_percent": min(100, max(0, progress_percent)),
            "xp_remaining": max(0, xp_for_next_level - xp_into_level),
        }
