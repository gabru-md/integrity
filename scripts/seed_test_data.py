from __future__ import annotations

import argparse
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path
from random import Random

from dotenv import load_dotenv

from gabru.qprocessor.qservice import QueueService
from gabru.qprocessor.qstats import QueueStats
from model.activity import Activity
from model.blog import BlogPost
from model.connection import Connection
from model.connection_interaction import ConnectionInteraction
from model.event import Event
from model.kanban_ticket import KanbanTicket
from model.notification import Notification
from model.project import Project, ProjectState
from model.promise import Promise
from model.report import Report
from model.skill import Skill
from model.skill_level_history import SkillLevelHistory
from model.thought import Thought
from model.timeline import TimelineItem
from model.user import User
from services.activities import ActivityService
from services.applications import ApplicationService
from services.blogs import BlogService
from services.connection_interactions import ConnectionInteractionService
from services.connections import ConnectionService
from services.events import EventService
from services.kanban_tickets import KanbanTicketService
from services.notifications import NotificationService
from services.projects import ProjectService
from services.promises import PromiseService
from services.reports import ReportService
from services.skill_level_history import SkillLevelHistoryService
from services.skills import SkillService
from services.thoughts import ThoughtService
from services.timeline import TimelineService
from services.users import UserService


APP_NAMES = [
    "Blogs",
    "Promises",
    "Events",
    "Thoughts",
    "Devices",
    "Projects",
    "KanbanTickets",
    "Activities",
    "Skills",
    "Connections",
    "Reports",
    "Users",
]


@dataclass
class SeedContext:
    now: datetime
    random: Random
    user_id: int


class SandboxSeeder:
    def __init__(self, now: datetime | None = None):
        self.now = now or datetime.now().replace(microsecond=0)
        self.random = Random(42)
        self.users = UserService()
        self.events = EventService()
        self.projects = ProjectService()
        self.timeline = TimelineService()
        self.activities = ActivityService()
        self.skills = SkillService()
        self.skill_history = SkillLevelHistoryService()
        self.promises = PromiseService()
        self.notifications = NotificationService()
        self.reports = ReportService()
        self.thoughts = ThoughtService()
        self.blogs = BlogService()
        self.connections = ConnectionService()
        self.interactions = ConnectionInteractionService()
        self.kanban = KanbanTicketService()
        self.applications = ApplicationService()
        self.queue = QueueService()

    def seed(self, scenario: str) -> dict:
        for app_name in APP_NAMES:
            self.applications.set_active_status(app_name, True)

        self.queue.create(QueueStats(name="sandbox-bootstrap", last_consumed_id=0))

        primary_user_id = self._create_user(
            username="sandbox",
            display_name="Sandbox User",
            password="sandbox",
            api_key="SBOX1",
            is_admin=True,
            ntfy_topic="rasbhari-sandbox",
        )
        self._create_user(
            username="observer",
            display_name="Observer User",
            password="sandbox",
            api_key="SBOX2",
            is_admin=False,
            ntfy_topic="rasbhari-observer",
        )

        context = SeedContext(now=self.now, random=self.random, user_id=primary_user_id)
        self._seed_minimal(context)

        if scenario == "realistic":
            self._seed_realistic_overlay(context)
        elif scenario == "project_heavy":
            self._seed_realistic_overlay(context)
            self._seed_project_heavy_overlay(context)
        elif scenario == "messy":
            self._seed_realistic_overlay(context)
            self._seed_messy_overlay(context)

        latest_event = self.events.get_recent_items(1)
        if latest_event:
            queue_stat = self.queue.find_one_by_field("name", "sandbox-bootstrap")
            if queue_stat:
                queue_stat.last_consumed_id = latest_event[0].id or 0
                self.queue.update(queue_stat)

        return {
            "username": "sandbox",
            "password": "sandbox",
            "api_key": "SBOX1",
            "scenario": scenario,
        }

    def _create_user(
        self,
        *,
        username: str,
        display_name: str,
        password: str,
        api_key: str,
        is_admin: bool,
        ntfy_topic: str,
    ) -> int:
        existing = self.users.get_by_username(username)
        if existing:
            return existing.id

        user = User(
            username=username,
            display_name=display_name,
            password=password,
            api_key=api_key,
            is_admin=is_admin,
            is_active=True,
            is_approved=True,
            ntfy_topic=ntfy_topic,
            created_at=self.now,
            updated_at=self.now,
        )
        user_id = self.users.create(user)
        if user_id is None:
            raise RuntimeError(f"Failed to create seed user {username}")
        return user_id

    def _seed_minimal(self, context: SeedContext) -> None:
        project_id = self._create_project(
            context,
            name="Sandbox Launchpad",
            project_type="Code",
            start_offset_days=12,
            state=ProjectState.ACTIVE,
            progress_count=2,
        )
        self._create_timeline_item(context, project_id, "Created sandbox project skeleton", 11, "Update")
        self._create_timeline_item(context, project_id, "Drafted first setup notes", 9, "Update")

        self._create_ticket(context, project_id, "Wire test data seeder", "Keep reset and reseed fast.", "in_progress", 5)
        self._create_ticket(context, project_id, "Document sandbox limits", "Call out what cannot be tested here.", "completed", 3)
        self._create_ticket(context, project_id, "Retire old docker notes", "Kept for reference only.", "shipped", 1, archived=True)

        self._create_activity(
            context,
            "Focused Coding Session",
            "coding:session",
            "Used when doing uninterrupted engineering work.",
            ["coding", "deepwork", "project:sandbox-launchpad"],
        )
        python_skill_id = self._create_skill(context, "Python", "python", ["py"], 420, "Ship the sandbox automation.")
        self._create_skill_history(context, python_skill_id, "Python", 3, 420, 4, "Reached level 3 in Python through repeated coding sessions.")
        self._create_promise(
            context,
            "Code daily",
            "Keep coding momentum visible.",
            "daily",
            target_event_tag="coding",
            required_count=1,
        )
        self._create_thought(context, "The sandbox should be deterministic enough for screenshots and demos.", 2)
        self._create_notification("ntfy", "Sandbox seed completed", 0.5)
        self._create_report(
            context,
            "weekly",
            0,
            "Sandbox Weekly Mirror",
            78,
            "The sandbox profile is active and useful for UI walkthroughs.",
            ["One project is already moving through a realistic board."],
        )
        self._create_blog(
            context,
            "Why the sandbox exists",
            "why-the-sandbox-exists",
            "This seeded instance exists to let you try project and dashboard features safely.",
            ["sandbox", "meta"],
            "published",
            6,
        )

        self._create_event(
            context,
            "coding:session",
            8,
            "Built out the first sandbox seeders",
            ["coding", "python", "project:sandbox-launchpad"],
        )
        self._create_event(
            context,
            "planning:review",
            3,
            "Reviewed which features belong in the sandbox",
            ["planning", "review"],
        )

        connection_id = self._create_connection(context, "Aarav", "Friend", 14, "High", ["close", "local"], 20)
        self._create_interaction(context, connection_id, "Aarav", "Call", "Phone", 25, 5, 4, ["friendship"])

    def _seed_realistic_overlay(self, context: SeedContext) -> None:
        home_id = self._create_project(context, "Home Systems Refresh", "DIY", 25, ProjectState.ACTIVE, 3)
        learning_id = self._create_project(context, "Personal Knowledge OS", "Other", 18, ProjectState.ACTIVE, 4)
        shipped_id = self._create_project(context, "Rasbhari Kanban", "Code", 21, ProjectState.COMPLETED, 6)

        self._create_timeline_item(context, home_id, "Defined device locations and cable cleanup goals", 22, "Update")
        self._create_timeline_item(context, learning_id, "Collected notes on recommendations and promises", 14, "Update")
        self._create_timeline_item(context, shipped_id, "Released the first project board workflow", 7, "Blog")

        self._create_ticket(context, home_id, "Install hallway beacon", "Needed for presence testing.", "backlog", 10)
        self._create_ticket(context, home_id, "Calibrate camera zone", "Tune false positive rate.", "prioritized", 8)
        self._create_ticket(context, learning_id, "Link repeated tags to skills", "Makes recommendations sharper.", "in_progress", 4)
        self._create_ticket(context, learning_id, "Review stale promises", "Need better alignment with events.", "completed", 2)
        self._create_ticket(context, shipped_id, "Archive shipped migration tasks", "Board cleanup after rollout.", "shipped", 1, archived=True)

        system_design_skill_id = self._create_skill(context, "System Design", "systemdesign", ["architecture"], 610, "Refine the test sandbox and recommendation loop.")
        writing_skill_id = self._create_skill(context, "Writing", "writing", ["notes"], 290, "Publish two short progress posts.")
        self._create_skill_history(context, system_design_skill_id, "System Design", 4, 610, 9, "Reached level 4 after several architecture sessions.")
        self._create_skill_history(context, writing_skill_id, "Writing", 2, 290, 5, "Reached level 2 by posting progress notes.")

        self._create_promise(context, "Write weekly", "Publish or draft at least one writing-related update each week.", "weekly", target_event_tag="writing", required_count=1)
        self._create_promise(context, "Avoid late-night doomscrolling", "Keep distraction usage low in the evening.", "daily", target_event_tag="distraction", required_count=0, is_negative=True, max_allowed=1)

        self._create_activity(context, "Morning Review", "planning:morning_review", "A short daily review of priorities and promises.", ["planning", "review"])
        self._create_activity(context, "Home Maintenance", "home:maintenance", "Capture work done on physical systems.", ["home", "maintenance"])

        self._create_thought(context, "The recommendations feature should probably prefer structural leverage over generic advice.", 6)
        self._create_thought(context, "Project boards work best when narrative updates and tickets stay linked but distinct.", 10)

        self._create_notification("email", "Weekly report queued for sandbox user", 1.2)
        self._create_report(context, "daily", 1, "Sandbox Daily Mirror", 84, "Signals are healthy, but one project looks stalled.", ["Kanban activity is strong.", "Home systems work needs one more real event."])

        self._create_blog(context, "Weekly Sandbox Review", "weekly-sandbox-review", "The seeded instance now exercises projects, skills, reports, and relationships together.", ["review", "sandbox"], "published", 3)

        self._create_event_series(
            context,
            [
                ("coding:session", "Implemented service-backed sandbox seeding", ["coding", "python", "project:rasbhari-kanban"]),
                ("writing:draft", "Wrote notes on recommendation ranking", ["writing", "notes", "project:personal-knowledge-os"]),
                ("planning:morning_review", "Reviewed priorities for the week", ["planning", "review"]),
                ("home:maintenance", "Organized cables and sensors", ["home", "maintenance", "project:home-systems-refresh"]),
                ("gaming:session", "Played a short match after work", ["recreation", "steam", "distraction"]),
            ],
            start_days_ago=14,
            step_days=2,
        )

        connection_id = self._create_connection(context, "Mom", "Family", 7, "High", ["family"], 30)
        self._create_interaction(context, connection_id, "Mom", "Call", "WhatsApp", 18, 5, 3, ["family"])
        self._create_interaction(context, connection_id, "Mom", "Text", "WhatsApp", 5, 4, 1, ["family"])

    def _seed_project_heavy_overlay(self, context: SeedContext) -> None:
        for idx in range(1, 4):
            project_id = self._create_project(
                context,
                name=f"Client Rollout {idx}",
                project_type="Code",
                start_offset_days=idx * 7,
                state=ProjectState.ACTIVE,
                progress_count=idx + 2,
            )
            self._create_timeline_item(context, project_id, f"Kicked off rollout tranche {idx}", idx * 6, "Update")
            self._create_ticket(context, project_id, f"Rollout checklist {idx}", "Track deployment steps.", "prioritized", idx * 4)
            self._create_ticket(context, project_id, f"Deploy slice {idx}", "Move from test to production.", "in_progress", idx * 3)
            self._create_ticket(context, project_id, f"Retro notes {idx}", "Capture what changed.", "completed", idx * 2)

        self._create_event_series(
            context,
            [
                ("deployment:prep", "Prepared a rollout checklist", ["deployment", "ops"]),
                ("deployment:ship", "Shipped a client slice", ["deployment", "shipping"]),
                ("review:retro", "Captured the rollout retro", ["review", "ops"]),
            ],
            start_days_ago=9,
            step_days=1,
        )

    def _seed_messy_overlay(self, context: SeedContext) -> None:
        project_id = self._create_project(context, "Messy Signals Lab", "Other", 11, ProjectState.ACTIVE, 1)
        self._create_ticket(context, project_id, "Untangle duplicate tags", "python, py, coding, code all overlap here.", "backlog", 7)
        self._create_ticket(context, project_id, "Review stale promises", "The promise definitions no longer match the event stream.", "prioritized", 4)

        self._create_event_series(
            context,
            [
                ("coding:session", "Used py tag this time", ["py", "deep_work"]),
                ("coding:session", "Used python tag next time", ["python", "focus"]),
                ("coding:session", "Used code tag on another day", ["code", "dev"]),
                ("reading:session", "Read but tagged as learn instead of reading", ["learn"]),
            ],
            start_days_ago=8,
            step_days=1,
        )
        self._create_promise(context, "Read daily", "This is intentionally misaligned with the current event tags.", "daily", target_event_tag="reading", required_count=1)

    def _create_project(self, context: SeedContext, name: str, project_type: str, start_offset_days: int, state: ProjectState, progress_count: int) -> int:
        project = Project(
            user_id=context.user_id,
            name=name,
            project_type=project_type,
            start_date=context.now - timedelta(days=start_offset_days),
            state=state,
            last_updated=context.now - timedelta(days=max(1, start_offset_days // 3)),
            progress_count=progress_count,
        )
        project_id = self.projects.create(project)
        if project_id is None:
            raise RuntimeError(f"Failed to create project {name}")
        return project_id

    def _create_timeline_item(self, context: SeedContext, project_id: int, content: str, days_ago: int, item_type: str) -> None:
        self.timeline.create(
            TimelineItem(
                user_id=context.user_id,
                project_id=project_id,
                content=content,
                timestamp=context.now - timedelta(days=days_ago),
                item_type=item_type,
            )
        )

    def _create_ticket(self, context: SeedContext, project_id: int, title: str, description: str, state: str, days_ago: int, *, archived: bool = False) -> None:
        timestamp = context.now - timedelta(days=days_ago)
        self.kanban.create(
            KanbanTicket(
                user_id=context.user_id,
                project_id=project_id,
                title=title,
                description=description,
                state=state,
                is_archived=archived,
                created_at=timestamp,
                updated_at=timestamp,
                state_changed_at=timestamp,
            )
        )

    def _create_activity(self, context: SeedContext, name: str, event_type: str, description: str, tags: list[str]) -> None:
        self.activities.create(
            Activity(
                user_id=context.user_id,
                name=name,
                event_type=event_type,
                description=description,
                tags=tags,
            )
        )

    def _create_skill(self, context: SeedContext, name: str, tag_key: str, aliases: list[str], total_xp: int, requirement: str) -> int:
        skill_id = self.skills.create(
            Skill(
                user_id=context.user_id,
                name=name,
                tag_key=tag_key,
                aliases=aliases,
                total_xp=total_xp,
                requirement=requirement,
            )
        )
        if skill_id is None:
            raise RuntimeError(f"Failed to create skill {name}")
        return skill_id

    def _create_skill_history(self, context: SeedContext, skill_id: int, skill_name: str, level: int, total_xp: int, days_ago: int, summary: str) -> None:
        self.skill_history.create(
            SkillLevelHistory(
                user_id=context.user_id,
                skill_id=skill_id,
                skill_name=skill_name,
                level=level,
                total_xp=total_xp,
                reached_at=context.now - timedelta(days=days_ago),
                summary=summary,
            )
        )

    def _create_promise(
        self,
        context: SeedContext,
        name: str,
        description: str,
        frequency: str,
        *,
        target_event_tag: str | None = None,
        target_event_type: str | None = None,
        required_count: int = 1,
        is_negative: bool = False,
        max_allowed: int = 0,
    ) -> None:
        self.promises.create(
            Promise(
                user_id=context.user_id,
                name=name,
                description=description,
                frequency=frequency,
                target_event_tag=target_event_tag,
                target_event_type=target_event_type,
                required_count=required_count,
                is_negative=is_negative,
                max_allowed=max_allowed,
                current_count=0,
                streak=2 if not is_negative else 0,
                best_streak=4 if not is_negative else 1,
                total_completions=5,
                total_periods=7,
                last_checked_at=context.now - timedelta(hours=10),
                next_check_at=context.now + timedelta(hours=14),
                created_at=context.now - timedelta(days=20),
                updated_at=context.now - timedelta(days=1),
            )
        )

    def _create_thought(self, context: SeedContext, message: str, days_ago: int) -> None:
        self.thoughts.create(
            Thought(
                user_id=context.user_id,
                message=message,
                created_at=context.now - timedelta(days=days_ago),
            )
        )

    def _create_notification(self, notification_type: str, notification_data: str, days_ago: float) -> None:
        self.notifications.create(
            Notification(
                notification_type=notification_type,
                notification_data=notification_data,
                created_at=self.now - timedelta(days=days_ago),
            )
        )

    def _create_report(self, context: SeedContext, report_type: str, days_ago: int, title: str, integrity_score: int, headline: str, observations: list[str]) -> None:
        period_end = context.now - timedelta(days=days_ago)
        period_start = period_end - timedelta(days=7 if report_type == "weekly" else 1)
        self.reports.upsert(
            Report(
                user_id=context.user_id,
                report_type=report_type,
                anchor_date=period_end.date().isoformat(),
                period_start=period_start,
                period_end=period_end,
                generated_at=period_end,
                title=title,
                integrity_score=integrity_score,
                headline=headline,
                observations=observations,
                metrics={"events_logged": 18, "projects_active": 3, "promises_tracked": 2},
                sections={"summary": observations},
            )
        )

    def _create_blog(self, context: SeedContext, title: str, slug: str, content: str, tags: list[str], status: str, days_ago: int) -> None:
        published_at = context.now - timedelta(days=days_ago)
        self.blogs.create(
            BlogPost(
                user_id=context.user_id,
                title=title,
                slug=slug,
                content=content,
                tags=tags,
                status=status,
                created_at=published_at,
                updated_at=published_at,
            )
        )

    def _create_connection(self, context: SeedContext, name: str, relationship_type: str, cadence_days: int, priority: str, tags: list[str], days_ago: int) -> int:
        connection_id = self.connections.create(
            Connection(
                user_id=context.user_id,
                name=name,
                relationship_type=relationship_type,
                cadence_days=cadence_days,
                priority=priority,
                notes="Seeded sandbox relationship.",
                tags=tags,
                active=True,
                created_at=context.now - timedelta(days=days_ago),
            )
        )
        if connection_id is None:
            raise RuntimeError(f"Failed to create connection {name}")
        return connection_id

    def _create_interaction(
        self,
        context: SeedContext,
        connection_id: int,
        connection_name: str,
        interaction_type: str,
        medium: str,
        duration_minutes: int,
        quality_score: int,
        days_ago: int,
        tags: list[str],
    ) -> None:
        self.interactions.create(
            ConnectionInteraction(
                user_id=context.user_id,
                connection_id=connection_id,
                connection_name=connection_name,
                interaction_type=interaction_type,
                medium=medium,
                duration_minutes=duration_minutes,
                quality_score=quality_score,
                notes="Seeded sandbox interaction.",
                tags=tags,
                created_at=context.now - timedelta(days=days_ago),
            )
        )

    def _create_event(self, context: SeedContext, event_type: str, days_ago: int, description: str, tags: list[str]) -> None:
        self.events.create(
            Event(
                user_id=context.user_id,
                event_type=event_type,
                timestamp=context.now - timedelta(days=days_ago),
                description=description,
                tags=tags,
            )
        )

    def _create_event_series(self, context: SeedContext, definitions: list[tuple[str, str, list[str]]], *, start_days_ago: int, step_days: int) -> None:
        day = start_days_ago
        for event_type, description, tags in definitions:
            self._create_event(context, event_type, day, description, tags)
            day -= step_days
            if day < 0:
                day = 0


def load_environment(env_file: str) -> None:
    load_dotenv(Path(env_file), override=True)


def main() -> None:
    parser = argparse.ArgumentParser(description="Seed deterministic Rasbhari sandbox data.")
    parser.add_argument("--env-file", default=".env.test", help="Environment file to load before seeding.")
    parser.add_argument(
        "--scenario",
        default="realistic",
        choices=["minimal", "realistic", "project_heavy", "messy"],
        help="Seed scenario to load.",
    )
    args = parser.parse_args()

    load_environment(args.env_file)

    result = SandboxSeeder().seed(args.scenario)
    print("Sandbox data seeded.")
    print(f"Scenario: {result['scenario']}")
    print(f"Login: {result['username']} / {result['password']}")
    print(f"API key: {result['api_key']}")


if __name__ == "__main__":
    main()
