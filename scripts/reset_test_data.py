from __future__ import annotations

import argparse
from pathlib import Path

import psycopg2
from dotenv import load_dotenv

def load_environment(env_file: str) -> None:
    load_dotenv(Path(env_file), override=True)


def build_service_bootstrap():
    from gabru.qprocessor.qservice import QueueService
    from services.activities import ActivityService
    from services.applications import ApplicationService
    from services.blogs import BlogService
    from services.connection_interactions import ConnectionInteractionService
    from services.connections import ConnectionService
    from services.devices import DeviceService
    from services.events import EventService
    from services.kanban_tickets import KanbanTicketService
    from services.network_signatures import NetworkSignatureService
    from services.notifications import NotificationService
    from services.projects import ProjectService
    from services.promises import PromiseService
    from services.reports import ReportService
    from services.skill_level_history import SkillLevelHistoryService
    from services.skills import SkillService
    from services.thoughts import ThoughtService
    from services.timeline import TimelineService
    from services.users import UserService

    return {
        "rasbhari": [
            UserService(),
            ApplicationService(),
            ProjectService(),
            TimelineService(),
            ActivityService(),
            SkillService(),
            SkillLevelHistoryService(),
            PromiseService(),
            ReportService(),
            DeviceService(),
            BlogService(),
            ConnectionService(),
            ConnectionInteractionService(),
            KanbanTicketService(),
            NetworkSignatureService(),
        ],
        "events": [EventService()],
        "queue": [QueueService()],
        "notifications": [NotificationService()],
        "thoughts": [ThoughtService()],
    }


def reset_database(db_name: str, services_by_db: dict) -> None:
    service = services_by_db[db_name][0]
    db = service.db
    conn = psycopg2.connect(
        dbname=db.dbname,
        user=db.user,
        password=db.password,
        host=db.host,
        port=db.port,
    )
    conn.autocommit = True
    with conn.cursor() as cursor:
        cursor.execute("DROP SCHEMA IF EXISTS public CASCADE")
        cursor.execute("CREATE SCHEMA public")
        cursor.execute("GRANT ALL ON SCHEMA public TO CURRENT_USER")
    conn.close()
    db.invalidate_connection()


def bootstrap_schema(services_by_db: dict) -> None:
    for services in services_by_db.values():
        for service in services:
            service.db.invalidate_connection()
            service._create_table()


def main() -> None:
    parser = argparse.ArgumentParser(description="Reset the Rasbhari sandbox databases and recreate schema.")
    parser.add_argument("--env-file", default=".env.test", help="Environment file to load before connecting.")
    args = parser.parse_args()

    load_environment(args.env_file)
    services_by_db = build_service_bootstrap()

    for db_name in services_by_db:
        reset_database(db_name, services_by_db)

    bootstrap_schema(services_by_db)
    print("Sandbox databases reset and schema recreated.")


if __name__ == "__main__":
    main()
