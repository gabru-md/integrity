import os
import unittest
from datetime import datetime
from unittest import mock

from flask import Flask

os.environ.setdefault("LOG_DIR", "/tmp/rasbhari-test-logs")

from apps.projects import _serialize_board_tickets
from gabru.flask.util import render_flask_template
from model.kanban_ticket import KanbanTicket
from model.project import Project, ProjectState
from model.user import User
from runtime.providers import RasbhariDashboardDataProvider
from services.kanban_tickets import KanbanTicketService

BASE_DIR = os.path.dirname(os.path.dirname(__file__))


class ProjectWorkLinkingTests(unittest.TestCase):
    def test_kanban_event_tags_include_project_work_and_focus_tags(self):
        project = Project(
            id=3,
            user_id=1,
            name="Rasbhari",
            project_type="Code",
            focus_tags=["python", "deep-work"],
            ticket_prefix="RSB",
            start_date=datetime(2026, 4, 2, 9, 0, 0),
            state=ProjectState.ACTIVE,
        )

        tags = KanbanTicketService._build_event_tags(project, "in_progress", 7, "prioritized")

        self.assertIn("project_work", tags)
        self.assertIn("project:rasbhari", tags)
        self.assertIn("project_work:rasbhari", tags)
        self.assertIn("python", tags)
        self.assertIn("deep-work", tags)
        self.assertIn("ticket_state:in_progress", tags)
        self.assertIn("ticket_previous_state:prioritized", tags)

    def test_notification_center_data_is_scoped_to_current_user(self):
        provider = RasbhariDashboardDataProvider(
            skill_service=mock.Mock(find_all=mock.Mock(return_value=[]), get_match_keys=mock.Mock(return_value=set()), count=mock.Mock(return_value=0)),
            activity_service=mock.Mock(get_recent_items=mock.Mock(return_value=[]), count=mock.Mock(return_value=0)),
            report_service=mock.Mock(get_recent_items=mock.Mock(return_value=[])),
            event_service=mock.Mock(find_all=mock.Mock(return_value=[])),
            notification_service=mock.Mock(
                get_in_app_notifications=mock.Mock(return_value=[
                    mock.Mock(
                        id=7,
                        title="Report ready",
                        notification_data="Your weekly report is ready.",
                        href="/reports/7/view",
                        notification_class="review",
                        created_at=datetime(2026, 4, 2, 12, 0, 0),
                    )
                ]),
                count_unread_in_app_notifications=mock.Mock(return_value=1),
            ),
            device_service=mock.Mock(),
            queue_service=mock.Mock(),
            skill_history_service=mock.Mock(),
            timeline_service=mock.Mock(),
        )

        app = Flask(__name__)
        with app.test_request_context("/"), mock.patch(
            "runtime.providers.PermissionManager.get_current_user",
            return_value=User(id=1, username="tester", display_name="Tester", experience_mode="everyday"),
        ):
            center = provider.get_notification_center_data()

        self.assertEqual(center["unread_count"], 1)
        self.assertEqual(center["items"][0]["title"], "Report ready")

    def test_project_board_template_renders_project_recommendations(self):
        app = Flask(__name__, template_folder=os.path.join(BASE_DIR, "templates"))
        app.secret_key = "test-secret"
        app.jinja_env.filters["projectdatetimeformat"] = lambda value: value.strftime("%b %d, %Y, %I:%M %p") if value else ""

        project = Project(
            id=3,
            user_id=1,
            name="Rasbhari",
            project_type="Code",
            focus_tags=["python"],
            ticket_prefix="RSB",
            start_date=datetime(2026, 4, 2, 9, 0, 0),
            state=ProjectState.ACTIVE,
        )

        with app.test_request_context("/projects/3/board"):
            rendered = render_flask_template(
                "project_board.html",
                project=project,
                initial_tickets=[],
                board_states=["backlog", "prioritized"],
                ticket_state_labels={"backlog": "Backlog", "prioritized": "Prioritized"},
                app_name="KanbanTickets",
                user_guidance={"overview": "Kanban guidance"},
                board_last_updated=None,
                archived_count=0,
                recent_activity=[],
                project_recommendations=[{
                    "id": "skill:3:python",
                    "title": "Create skill for python",
                    "body": "Project work on Rasbhari already emits `python`.",
                    "action": "create_skill",
                    "action_label": "Stage Skill",
                    "kind": "stage_action",
                    "confidence": 0.82,
                    "reasoning": "This project already has a stable focus tag but no matching skill.",
                    "scope": "item",
                    "scope_id": 3,
                }],
                PermissionManager=mock.Mock(can_view_app=lambda *_: False),
                active_app_names=set(),
                current_user={"id": 1, "username": "tester", "display_name": "Tester", "is_admin": False, "onboarding_completed": True},
                Role=mock.Mock(),
            )

        self.assertIn("Recommendations", rendered)
        self.assertIn("Create skill for python", rendered)
        self.assertIn("Stage Skill", rendered)

    def test_board_ticket_serialization_includes_dependencies(self):
        project = Project(
            id=3,
            user_id=1,
            name="Rasbhari",
            project_type="Code",
            focus_tags=["python"],
            ticket_prefix="RSB",
            start_date=datetime(2026, 4, 2, 9, 0, 0),
            state=ProjectState.ACTIVE,
        )
        dependency_ticket = KanbanTicket(
            id=4,
            user_id=1,
            project_id=3,
            ticket_code="RSB-4",
            title="Set up event pipeline",
            description="",
            state="prioritized",
        )
        ticket = KanbanTicket(
            id=7,
            user_id=1,
            project_id=3,
            ticket_code="RSB-7",
            title="Build promise linking",
            description="",
            dependency_ticket_ids=[4],
            state="backlog",
        )

        with mock.patch("apps.projects._build_promise_index", return_value=[]), \
             mock.patch("apps.projects._build_skill_index", return_value=[]):
            serialized = _serialize_board_tickets(project, [ticket, dependency_ticket])

        serialized_ticket = next(item for item in serialized if item["id"] == 7)
        self.assertEqual(serialized_ticket["dependencies"][0]["id"], 4)
        self.assertEqual(serialized_ticket["dependencies"][0]["ticket_code"], "RSB-4")
        self.assertTrue(any(item["id"] == 4 for item in serialized_ticket["available_dependencies"]))


if __name__ == "__main__":
    unittest.main()
