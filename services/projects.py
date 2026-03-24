from typing import List, Optional
from gabru.db.db import DB
from gabru.db.service import CRUDService
from model.project import Project


class ProjectService(CRUDService[Project]):
    def __init__(self):
        super().__init__("projects", DB("rasbhari"))

    def _create_table(self):
        if self.db.conn:
            with self.db.conn.cursor() as cursor:
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS projects (
                        id SERIAL PRIMARY KEY,
                        name VARCHAR(255) NOT NULL UNIQUE,
                        project_type VARCHAR(50),
                        start_date TIMESTAMP,
                        state VARCHAR(50),
                        last_updated TIMESTAMP,
                        progress_count INTEGER DEFAULT 0
                    )
                """)
                self.db.conn.commit()

    def _to_tuple(self, entity: Project) -> tuple:
        return (
            entity.name, entity.project_type, entity.start_date,
            entity.state.value, entity.last_updated, entity.progress_count
        )

    def _to_object(self, row: tuple) -> Project:
        return Project(
            id=row[0], name=row[1], project_type=row[2], start_date=row[3],
            state=row[4], last_updated=row[5], progress_count=row[6]
        )

    def _get_columns_for_insert(self) -> List[str]:
        return ["name", "project_type", "start_date", "state", "last_updated", "progress_count"]

    def _get_columns_for_update(self) -> List[str]:
        return ["name", "project_type", "start_date", "state", "last_updated", "progress_count"]

    def _get_columns_for_select(self) -> List[str]:
        return ["id", "name", "project_type", "start_date", "state", "last_updated", "progress_count"]

    def get_by_name(self, name: str) -> Optional[Project]:
        """Fetches a single project by its unique name."""
        return self.find_one_by_field("name", name)

