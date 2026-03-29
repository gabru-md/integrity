from typing import List, Optional
from gabru.db.db import DB
from gabru.db.service import CRUDService
from model.application import Application

class ApplicationService(CRUDService[Application]):
    def __init__(self):
        super().__init__("applications", DB("rasbhari"))

    def _create_table(self):
        if self.db.get_conn():
            with self.db.get_conn().cursor() as cursor:
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS applications (
                        id SERIAL PRIMARY KEY,
                        name VARCHAR(100) NOT NULL UNIQUE,
                        is_active BOOLEAN NOT NULL DEFAULT TRUE,
                        description TEXT
                    )
                """)
                self.db.get_conn().commit()

    def _to_tuple(self, obj: Application) -> tuple:
        return (obj.name, obj.is_active, obj.description)

    def _to_object(self, row: tuple) -> Application:
        return Application(
            id=row[0],
            name=row[1],
            is_active=row[2],
            description=row[3]
        )

    def _get_columns_for_insert(self) -> List[str]:
        return ["name", "is_active", "description"]

    def _get_columns_for_update(self) -> List[str]:
        return ["name", "is_active", "description"]

    def _get_columns_for_select(self) -> List[str]:
        return ["id", "name", "is_active", "description"]

    def get_by_name(self, name: str) -> Optional[Application]:
        return self.find_one_by_field("name", name)

    def set_active_status(self, name: str, is_active: bool) -> bool:
        app = self.get_by_name(name)
        if app:
            app.is_active = is_active
            return self.update(app)
        else:
            new_app = Application(name=name, is_active=is_active)
            return self.create(new_app) is not None
