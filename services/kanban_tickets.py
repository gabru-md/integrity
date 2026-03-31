from datetime import datetime
from typing import List, Optional

from gabru.db.db import DB
from gabru.db.service import CRUDService
from gabru.log import Logger
from model.kanban_ticket import KanbanTicket
from services.eventing import emit_event_safely
from services.projects import ProjectService


class KanbanTicketService(CRUDService[KanbanTicket]):
    STATE_ORDER = ["backlog", "prioritized", "in_progress", "completed", "shipped"]

    def __init__(self):
        super().__init__("kanban_tickets", DB("rasbhari"), user_scoped=True)
        self.project_service = ProjectService()
        self.log = Logger.get_log("KanbanTicketService")

    def _create_table(self):
        if self.db.conn:
            with self.db.conn.cursor() as cursor:
                cursor.execute(
                    """
                    CREATE TABLE IF NOT EXISTS kanban_tickets (
                        id SERIAL PRIMARY KEY,
                        user_id INTEGER NOT NULL,
                        project_id INTEGER NOT NULL,
                        title VARCHAR(255) NOT NULL,
                        description TEXT,
                        state VARCHAR(50) NOT NULL DEFAULT 'backlog',
                        is_archived BOOLEAN NOT NULL DEFAULT FALSE,
                        created_at TIMESTAMP NOT NULL DEFAULT NOW(),
                        updated_at TIMESTAMP NOT NULL DEFAULT NOW(),
                        state_changed_at TIMESTAMP NOT NULL DEFAULT NOW()
                    )
                    """
                )
                cursor.execute("ALTER TABLE kanban_tickets ADD COLUMN IF NOT EXISTS description TEXT")
                cursor.execute("ALTER TABLE kanban_tickets ADD COLUMN IF NOT EXISTS state VARCHAR(50) NOT NULL DEFAULT 'backlog'")
                cursor.execute("ALTER TABLE kanban_tickets ADD COLUMN IF NOT EXISTS is_archived BOOLEAN NOT NULL DEFAULT FALSE")
                cursor.execute("ALTER TABLE kanban_tickets ADD COLUMN IF NOT EXISTS created_at TIMESTAMP NOT NULL DEFAULT NOW()")
                cursor.execute("ALTER TABLE kanban_tickets ADD COLUMN IF NOT EXISTS updated_at TIMESTAMP NOT NULL DEFAULT NOW()")
                cursor.execute("ALTER TABLE kanban_tickets ADD COLUMN IF NOT EXISTS state_changed_at TIMESTAMP NOT NULL DEFAULT NOW()")
                cursor.execute("CREATE INDEX IF NOT EXISTS idx_kanban_tickets_project_state ON kanban_tickets(project_id, state)")
                self.db.conn.commit()

    def _to_tuple(self, entity: KanbanTicket) -> tuple:
        state_value = entity.state.value if hasattr(entity.state, "value") else entity.state
        return (
            entity.user_id,
            entity.project_id,
            entity.title,
            entity.description,
            state_value,
            entity.is_archived,
            entity.created_at,
            entity.updated_at,
            entity.state_changed_at,
        )

    def _to_object(self, row: tuple) -> KanbanTicket:
        return KanbanTicket(
            id=row[0],
            user_id=row[1],
            project_id=row[2],
            title=row[3],
            description=row[4] or "",
            state=row[5],
            is_archived=bool(row[6]),
            created_at=row[7],
            updated_at=row[8],
            state_changed_at=row[9],
        )

    def _get_columns_for_insert(self) -> List[str]:
        return ["user_id", "project_id", "title", "description", "state", "is_archived", "created_at", "updated_at", "state_changed_at"]

    def _get_columns_for_update(self) -> List[str]:
        return ["user_id", "project_id", "title", "description", "state", "is_archived", "created_at", "updated_at", "state_changed_at"]

    def _get_columns_for_select(self) -> List[str]:
        return ["id", "user_id", "project_id", "title", "description", "state", "is_archived", "created_at", "updated_at", "state_changed_at"]

    def create(self, obj: KanbanTicket) -> Optional[int]:
        now = datetime.now()
        obj.created_at = obj.created_at or now
        obj.updated_at = now
        obj.state_changed_at = obj.state_changed_at or now
        ticket_id = super().create(obj)
        if ticket_id:
            project = self.project_service.get_by_id(obj.project_id)
            emit_event_safely(
                self.log,
                user_id=obj.user_id,
                event_type="kanban:ticket_created",
                timestamp=now,
                description=f"Created ticket '{obj.title}'",
                tags=self._build_event_tags(project.name if project else None, obj.state, ticket_id),
            )
        return ticket_id

    def update(self, obj: KanbanTicket) -> bool:
        existing = self.get_by_id(obj.id) if obj.id is not None else None
        if not existing:
            return False
        now = datetime.now()
        new_state = obj.state.value if hasattr(obj.state, "value") else obj.state
        old_state = existing.state.value if hasattr(existing.state, "value") else existing.state
        obj.created_at = existing.created_at
        obj.updated_at = now
        obj.state_changed_at = now if new_state != old_state else existing.state_changed_at
        updated = super().update(obj)
        if updated:
            project = self.project_service.get_by_id(obj.project_id)
            if new_state != old_state:
                emit_event_safely(
                    self.log,
                    user_id=obj.user_id,
                    event_type="kanban:ticket_moved",
                    timestamp=now,
                    description=f"Moved ticket '{obj.title}' from {old_state} to {new_state}",
                    tags=self._build_event_tags(project.name if project else None, new_state, obj.id, old_state),
                )
            else:
                emit_event_safely(
                    self.log,
                    user_id=obj.user_id,
                    event_type="kanban:ticket_updated",
                    timestamp=now,
                    description=f"Updated ticket '{obj.title}'",
                    tags=self._build_event_tags(project.name if project else None, new_state, obj.id),
                )
        return updated

    def get_by_project_id(self, project_id: int, include_archived: bool = True) -> List[KanbanTicket]:
        filters = {"project_id": project_id}
        if not include_archived:
            filters["is_archived"] = False
        return self.find_all(filters=filters, sort_by={"id": "DESC"})

    def move_ticket(self, ticket_id: int, state: str) -> Optional[KanbanTicket]:
        normalized_state = (state or "").strip().lower().replace("-", "_")
        if normalized_state not in self.STATE_ORDER:
            raise ValueError("Invalid ticket state")
        ticket = self.get_by_id(ticket_id)
        if not ticket:
            return None
        ticket.state = normalized_state
        if self.update(ticket):
            return self.get_by_id(ticket_id)
        return None

    def next_state(self, state: str) -> str:
        normalized_state = (state or "").strip().lower().replace("-", "_")
        if normalized_state not in self.STATE_ORDER:
            return self.STATE_ORDER[0]
        index = self.STATE_ORDER.index(normalized_state)
        return self.STATE_ORDER[min(index + 1, len(self.STATE_ORDER) - 1)]

    def archive_ticket(self, ticket_id: int) -> Optional[KanbanTicket]:
        ticket = self.get_by_id(ticket_id)
        if not ticket:
            return None
        if ticket.is_archived:
            return ticket
        ticket.is_archived = True
        if self.update(ticket):
            project = self.project_service.get_by_id(ticket.project_id)
            emit_event_safely(
                self.log,
                user_id=ticket.user_id,
                event_type="kanban:ticket_archived",
                timestamp=datetime.now(),
                description=f"Archived ticket '{ticket.title}'",
                tags=self._build_event_tags(project.name if project else None, ticket.state, ticket.id),
            )
            return self.get_by_id(ticket_id)
        return None

    @staticmethod
    def _build_event_tags(project_name: Optional[str], state_value, ticket_id: Optional[int], previous_state: Optional[str] = None) -> List[str]:
        tags = ["kanban"]
        if project_name:
            tags.append(f"project:{project_name.strip().lower().replace(' ', '-')}")
        normalized_state = state_value.value if hasattr(state_value, "value") else state_value
        if normalized_state:
            tags.append(f"ticket_state:{normalized_state}")
        if previous_state:
            tags.append(f"ticket_previous_state:{previous_state}")
        if ticket_id is not None:
            tags.append(f"ticket:{ticket_id}")
        return tags
