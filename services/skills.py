from typing import List, Optional

from gabru.db.db import DB
from gabru.db.service import CRUDService
from model.skill import Skill


class SkillService(CRUDService[Skill]):
    def __init__(self):
        super().__init__("skills", DB("rasbhari"), user_scoped=True)

    def _create_table(self):
        if self.db.conn:
            with self.db.conn.cursor() as cursor:
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS skills (
                        id SERIAL PRIMARY KEY,
                        user_id INTEGER NOT NULL,
                        name VARCHAR(255) NOT NULL,
                        tag_key VARCHAR(255) DEFAULT '',
                        aliases TEXT[] DEFAULT ARRAY[]::TEXT[],
                        level INTEGER NOT NULL DEFAULT 1,
                        total_xp INTEGER NOT NULL DEFAULT 0,
                        requirement TEXT DEFAULT '',
                        UNIQUE(user_id, name)
                    )
                """)
                self.db.conn.commit()

    def _to_tuple(self, entity: Skill) -> tuple:
        tag_key = entity.tag_key or entity.name
        aliases = entity.aliases or []
        return entity.user_id, entity.name, tag_key, aliases, entity.level, entity.total_xp, entity.requirement

    def _to_object(self, row: tuple) -> Skill:
        return Skill(
            id=row[0],
            user_id=row[1],
            name=row[2],
            tag_key=row[3] or row[2],
            aliases=row[4] or [],
            level=row[5],
            total_xp=row[6],
            requirement=row[7] or ""
        )

    def _get_columns_for_insert(self) -> List[str]:
        return ["user_id", "name", "tag_key", "aliases", "level", "total_xp", "requirement"]

    def _get_columns_for_update(self) -> List[str]:
        return ["user_id", "name", "tag_key", "aliases", "level", "total_xp", "requirement"]

    def _get_columns_for_select(self) -> List[str]:
        return ["id", "user_id", "name", "tag_key", "aliases", "level", "total_xp", "requirement"]

    def get_by_name(self, name: str) -> Optional[Skill]:
        return self.find_one_by_field("name", name)

    @staticmethod
    def normalize_skill_tag(value: str) -> str:
        value = value.strip().lower().lstrip("#")
        return "".join(char for char in value if char.isalnum())

    @classmethod
    def get_match_keys(cls, skill: Skill) -> set[str]:
        candidates = [skill.tag_key or skill.name, skill.name, *(skill.aliases or [])]
        return {
            normalized for normalized in (cls.normalize_skill_tag(candidate) for candidate in candidates)
            if normalized
        }

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
            "tag_key": skill.tag_key or skill.name,
            "aliases": skill.aliases or [],
            "level": level,
            "total_xp": skill.total_xp,
            "requirement": skill.requirement,
            "xp_into_level": xp_into_level,
            "xp_for_next_level": xp_for_next_level,
            "progress_percent": min(100, max(0, progress_percent)),
            "xp_remaining": max(0, xp_for_next_level - xp_into_level),
        }
