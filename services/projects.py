from typing import List, Optional
from gabru.db.db import DB
from gabru.db.service import CRUDService
from model.project import Project


class ProjectService(CRUDService[Project]):
    def __init__(self):
        super().__init__("projects", DB("rasbhari"), user_scoped=True)

    def _create_table(self):
        if self.db.conn:
            with self.db.conn.cursor() as cursor:
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS projects (
                        id SERIAL PRIMARY KEY,
                        user_id INTEGER NOT NULL,
                        name VARCHAR(255) NOT NULL,
                        project_type VARCHAR(50),
                        focus_tags TEXT[] DEFAULT ARRAY[]::TEXT[],
                        ticket_prefix VARCHAR(32),
                        start_date TIMESTAMP,
                        state VARCHAR(50),
                        last_updated TIMESTAMP,
                        progress_count INTEGER DEFAULT 0,
                        UNIQUE(user_id, name)
                    )
                """)
                cursor.execute("ALTER TABLE projects ADD COLUMN IF NOT EXISTS focus_tags TEXT[] DEFAULT ARRAY[]::TEXT[]")
                cursor.execute("ALTER TABLE projects ADD COLUMN IF NOT EXISTS ticket_prefix VARCHAR(32)")
                self.db.conn.commit()

    def _to_tuple(self, entity: Project) -> tuple:
        return (
            entity.user_id, entity.name, entity.project_type, entity.focus_tags or [], entity.ticket_prefix, entity.start_date,
            entity.state.value, entity.last_updated, entity.progress_count
        )

    def _to_object(self, row: tuple) -> Project:
        return Project(
            id=row[0], user_id=row[1], name=row[2], project_type=row[3], focus_tags=row[4] or [], ticket_prefix=row[5], start_date=row[6],
            state=row[7], last_updated=row[8], progress_count=row[9]
        )

    def _get_columns_for_insert(self) -> List[str]:
        return ["user_id", "name", "project_type", "focus_tags", "ticket_prefix", "start_date", "state", "last_updated", "progress_count"]

    def _get_columns_for_update(self) -> List[str]:
        return ["user_id", "name", "project_type", "focus_tags", "ticket_prefix", "start_date", "state", "last_updated", "progress_count"]

    def _get_columns_for_select(self) -> List[str]:
        return ["id", "user_id", "name", "project_type", "focus_tags", "ticket_prefix", "start_date", "state", "last_updated", "progress_count"]

    def get_by_name(self, name: str) -> Optional[Project]:
        """Fetches a single project by its unique name."""
        return self.find_one_by_field("name", name)
