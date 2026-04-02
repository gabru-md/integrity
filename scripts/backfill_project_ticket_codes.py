from __future__ import annotations

from pathlib import Path

from dotenv import load_dotenv

from services.kanban_tickets import KanbanTicketService
from services.projects import ProjectService


PROJECT_PREFIXES = {
    "Rasbhari": "RSB",
    "Explorer": "EXP",
    "Mini Camera": "MCAM",
    "Apothecary Alpha": "APOT",
}


def main() -> None:
    load_dotenv(Path(".env"), override=False)

    project_service = ProjectService()
    ticket_service = KanbanTicketService()

    for project_name, ticket_prefix in PROJECT_PREFIXES.items():
        project = project_service.get_by_name(project_name)
        if not project or project.id is None:
            print(f"skip {project_name}: project not found")
            continue

        project.ticket_prefix = ticket_prefix
        project_service.update(project)
        updated = ticket_service.backfill_ticket_codes_for_project(project.id, prefix=ticket_prefix)
        print(f"{project_name} -> {ticket_prefix}: backfilled {updated} ticket(s)")


if __name__ == "__main__":
    main()
