from datetime import datetime
import json
from typing import List, Optional

from gabru.db.db import DB
from gabru.db.service import CRUDService
from gabru.log import Logger
from model.kanban_ticket import KanbanTicket
from services.eventing import emit_event_safely
from services.projects import ProjectService


class KanbanTicketService(CRUDService[KanbanTicket]):
    STATE_ORDER = ["backlog", "prioritized", "in_progress", "completed", "shipped"]
    TICKET_SIGNAL_EVENT_TYPES = (
        "kanban:ticket_created",
        "kanban:ticket_moved",
        "kanban:ticket_updated",
        "kanban:ticket_archived",
    )

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
                        ticket_code VARCHAR(64),
                        title VARCHAR(255) NOT NULL,
                        description TEXT,
                        dependency_ticket_ids TEXT NOT NULL DEFAULT '[]',
                        state VARCHAR(50) NOT NULL DEFAULT 'backlog',
                        is_archived BOOLEAN NOT NULL DEFAULT FALSE,
                        created_at TIMESTAMP NOT NULL DEFAULT NOW(),
                        updated_at TIMESTAMP NOT NULL DEFAULT NOW(),
                        state_changed_at TIMESTAMP NOT NULL DEFAULT NOW()
                    )
                    """
                )
                cursor.execute("ALTER TABLE kanban_tickets ADD COLUMN IF NOT EXISTS ticket_code VARCHAR(64)")
                cursor.execute("ALTER TABLE kanban_tickets ADD COLUMN IF NOT EXISTS description TEXT")
                cursor.execute("ALTER TABLE kanban_tickets ADD COLUMN IF NOT EXISTS dependency_ticket_ids TEXT NOT NULL DEFAULT '[]'")
                cursor.execute("ALTER TABLE kanban_tickets ADD COLUMN IF NOT EXISTS state VARCHAR(50) NOT NULL DEFAULT 'backlog'")
                cursor.execute("ALTER TABLE kanban_tickets ADD COLUMN IF NOT EXISTS is_archived BOOLEAN NOT NULL DEFAULT FALSE")
                cursor.execute("ALTER TABLE kanban_tickets ADD COLUMN IF NOT EXISTS created_at TIMESTAMP NOT NULL DEFAULT NOW()")
                cursor.execute("ALTER TABLE kanban_tickets ADD COLUMN IF NOT EXISTS updated_at TIMESTAMP NOT NULL DEFAULT NOW()")
                cursor.execute("ALTER TABLE kanban_tickets ADD COLUMN IF NOT EXISTS state_changed_at TIMESTAMP NOT NULL DEFAULT NOW()")
                cursor.execute("CREATE UNIQUE INDEX IF NOT EXISTS idx_kanban_tickets_project_code ON kanban_tickets(project_id, ticket_code) WHERE ticket_code IS NOT NULL")
                cursor.execute("CREATE INDEX IF NOT EXISTS idx_kanban_tickets_project_state ON kanban_tickets(project_id, state)")
                self.db.conn.commit()

    def _to_tuple(self, entity: KanbanTicket) -> tuple:
        state_value = entity.state.value if hasattr(entity.state, "value") else entity.state
        return (
            entity.user_id,
            entity.project_id,
            entity.ticket_code,
            entity.title,
            entity.description,
            json.dumps(self._normalize_dependency_ids(entity.dependency_ticket_ids)),
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
            ticket_code=row[3],
            title=row[4],
            description=row[5] or "",
            dependency_ticket_ids=self._parse_dependency_ids(row[6]),
            state=row[7],
            is_archived=bool(row[8]),
            created_at=row[9],
            updated_at=row[10],
            state_changed_at=row[11],
        )

    def _get_columns_for_insert(self) -> List[str]:
        return ["user_id", "project_id", "ticket_code", "title", "description", "dependency_ticket_ids", "state", "is_archived", "created_at", "updated_at", "state_changed_at"]

    def _get_columns_for_update(self) -> List[str]:
        return ["user_id", "project_id", "ticket_code", "title", "description", "dependency_ticket_ids", "state", "is_archived", "created_at", "updated_at", "state_changed_at"]

    def _get_columns_for_select(self) -> List[str]:
        return ["id", "user_id", "project_id", "ticket_code", "title", "description", "dependency_ticket_ids", "state", "is_archived", "created_at", "updated_at", "state_changed_at"]

    def create(self, obj: KanbanTicket) -> Optional[int]:
        now = datetime.now()
        obj.created_at = obj.created_at or now
        obj.updated_at = now
        obj.state_changed_at = obj.state_changed_at or now
        if not obj.ticket_code:
            obj.ticket_code = self._issue_ticket_code(obj.project_id)
        ticket_id = super().create(obj)
        if ticket_id:
            project = self.project_service.get_by_id(obj.project_id)
            emit_event_safely(
                self.log,
                user_id=obj.user_id,
                event_type="kanban:ticket_created",
                timestamp=now,
                description=f"Created ticket '{obj.title}'",
                tags=self._build_event_tags(project, obj.state, ticket_id),
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
        obj.ticket_code = existing.ticket_code
        obj.dependency_ticket_ids = self._normalize_dependency_ids(obj.dependency_ticket_ids)
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
                    tags=self._build_event_tags(project, new_state, obj.id, old_state),
                )
            else:
                emit_event_safely(
                    self.log,
                    user_id=obj.user_id,
                    event_type="kanban:ticket_updated",
                    timestamp=now,
                    description=f"Updated ticket '{obj.title}'",
                    tags=self._build_event_tags(project, new_state, obj.id),
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
                tags=self._build_event_tags(project, ticket.state, ticket.id),
            )
            return self.get_by_id(ticket_id)
        return None

    def update_dependencies(self, ticket_id: int, dependency_ticket_ids: list[int]) -> Optional[KanbanTicket]:
        ticket = self.get_by_id(ticket_id)
        if not ticket:
            return None

        normalized_ids = self._normalize_dependency_ids(dependency_ticket_ids)
        if ticket_id in normalized_ids:
            raise ValueError("A ticket cannot depend on itself")

        if normalized_ids:
            dependency_tickets = [self.get_by_id(dependency_id) for dependency_id in normalized_ids]
            if any(dependency_ticket is None for dependency_ticket in dependency_tickets):
                raise ValueError("Dependency ticket not found")
            if any(dependency_ticket.project_id != ticket.project_id for dependency_ticket in dependency_tickets):
                raise ValueError("Dependencies must belong to the same project")

        ticket.dependency_ticket_ids = normalized_ids
        if self.update(ticket):
            return self.get_by_id(ticket_id)
        return None

    def _issue_ticket_code(self, project_id: int) -> Optional[str]:
        project = self.project_service.get_by_id(project_id)
        prefix = getattr(project, "ticket_prefix", None) if project else None
        if not prefix:
            return None

        def operation(conn):
            with conn.cursor() as cursor:
                cursor.execute(
                    """
                    SELECT ticket_code
                    FROM kanban_tickets
                    WHERE project_id = %s AND ticket_code IS NOT NULL
                    ORDER BY id ASC
                    """,
                    (project_id,),
                )
                max_sequence = 0
                prefix_with_dash = f"{prefix}-"
                for row in cursor.fetchall():
                    code = row[0] or ""
                    if code.startswith(prefix_with_dash):
                        suffix = code[len(prefix_with_dash):]
                        if suffix.isdigit():
                            max_sequence = max(max_sequence, int(suffix))
                return f"{prefix}-{max_sequence + 1}"

        return self._run_with_connection_retry(operation, fallback=None, action_name="issue kanban ticket code")

    def backfill_ticket_codes_for_project(self, project_id: int, prefix: Optional[str] = None) -> int:
        project = self.project_service.get_by_id(project_id)
        if not project:
            return 0
        effective_prefix = prefix or getattr(project, "ticket_prefix", None)
        if not effective_prefix:
            return 0

        def operation(conn):
            with conn.cursor() as cursor:
                cursor.execute(
                    """
                    SELECT id, ticket_code
                    FROM kanban_tickets
                    WHERE project_id = %s
                    ORDER BY id ASC
                    """,
                    (project_id,),
                )
                next_sequence = 1
                updates = []
                prefix_with_dash = f"{effective_prefix}-"
                for ticket_id, ticket_code in cursor.fetchall():
                    if ticket_code:
                        if ticket_code.startswith(prefix_with_dash):
                            suffix = ticket_code[len(prefix_with_dash):]
                            if suffix.isdigit():
                                next_sequence = max(next_sequence, int(suffix) + 1)
                        continue
                    updates.append((f"{effective_prefix}-{next_sequence}", ticket_id))
                    next_sequence += 1
                for ticket_code, ticket_id in updates:
                    cursor.execute(
                        "UPDATE kanban_tickets SET ticket_code = %s WHERE id = %s",
                        (ticket_code, ticket_id),
                    )
                conn.commit()
                return len(updates)

        return self._run_with_connection_retry(operation, fallback=0, action_name="backfill kanban ticket codes")

    @staticmethod
    def _build_event_tags(project, state_value, ticket_id: Optional[int], previous_state: Optional[str] = None) -> List[str]:
        tags = ["kanban", "project_work"]
        project_name = getattr(project, "name", None)
        if project_name:
            project_slug = project_name.strip().lower().replace(' ', '-')
            tags.extend([
                f"project:{project_slug}",
                f"project_work:{project_slug}",
            ])
        for focus_tag in getattr(project, "focus_tags", []) or []:
            normalized_tag = str(focus_tag).strip().lower()
            if normalized_tag:
                tags.append(normalized_tag)
        normalized_state = state_value.value if hasattr(state_value, "value") else state_value
        if normalized_state:
            tags.append(f"ticket_state:{normalized_state}")
        if previous_state:
            tags.append(f"ticket_previous_state:{previous_state}")
        if ticket_id is not None:
            tags.append(f"ticket:{ticket_id}")
        return tags

    @classmethod
    def build_ticket_signal(cls, project, ticket: KanbanTicket) -> dict:
        return {
            "event_types": list(cls.TICKET_SIGNAL_EVENT_TYPES),
            "tags": cls._build_event_tags(project, ticket.state, ticket.id),
        }

    @staticmethod
    def _parse_dependency_ids(raw_value) -> list[int]:
        if raw_value in (None, ""):
            return []
        if isinstance(raw_value, list):
            return KanbanTicketService._normalize_dependency_ids(raw_value)
        try:
            parsed = json.loads(raw_value)
        except (TypeError, ValueError):
            return []
        return KanbanTicketService._normalize_dependency_ids(parsed)

    @staticmethod
    def _normalize_dependency_ids(values) -> list[int]:
        normalized = []
        for value in values or []:
            try:
                int_value = int(value)
            except (TypeError, ValueError):
                continue
            if int_value not in normalized:
                normalized.append(int_value)
        return normalized
