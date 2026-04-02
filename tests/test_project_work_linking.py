import os
import unittest
from datetime import datetime
from unittest import mock

from flask import Flask

os.environ.setdefault("LOG_DIR", "/tmp/rasbhari-test-logs")

from gabru.flask.util import render_flask_template
from model.kanban_ticket import KanbanTicket
from model.project import Project, ProjectState
from model.promise import Promise
from model.skill import Skill
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

    def test_today_data_explains_project_contribution(self):
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
        ticket = KanbanTicket(
            id=9,
            user_id=1,
            project_id=3,
            ticket_code="RSB-9",
            title="Build project linking",
            description="Make project work visible to promises and skills",
            state="in_progress",
            created_at=datetime(2026, 4, 2, 9, 0, 0),
            updated_at=datetime(2026, 4, 2, 10, 0, 0),
            state_changed_at=datetime(2026, 4, 2, 10, 0, 0),
        )
        promise = Promise(
            id=5,
            user_id=1,
            name="Daily deep work",
            description="",
            frequency="daily",
            target_event_tag="deep-work",
            target_event_type=None,
            required_count=1,
        )
        skill = Skill(id=8, user_id=1, name="Python", tag_key="python", aliases=[])

        provider = RasbhariDashboardDataProvider(
            project_service=mock.Mock(find_all=mock.Mock(return_value=[project]), count=mock.Mock(return_value=1)),
            kanban_ticket_service=mock.Mock(get_by_project_id=mock.Mock(return_value=[ticket]), count=mock.Mock(return_value=1), find_all=mock.Mock(return_value=[ticket])),
            promise_service=mock.Mock(get_due_promises=mock.Mock(return_value=[]), find_all=mock.Mock(return_value=[promise]), count=mock.Mock(return_value=1)),
            skill_service=mock.Mock(find_all=mock.Mock(return_value=[skill]), get_match_keys=mock.Mock(return_value={"python"}), count=mock.Mock(return_value=1)),
            connection_service=mock.Mock(get_active=mock.Mock(return_value=[])),
            activity_service=mock.Mock(get_recent_items=mock.Mock(return_value=[]), count=mock.Mock(return_value=1)),
            report_service=mock.Mock(get_recent_items=mock.Mock(return_value=[])),
            event_service=mock.Mock(find_all=mock.Mock(return_value=[])),
            notification_service=mock.Mock(),
            device_service=mock.Mock(),
            queue_service=mock.Mock(),
            skill_history_service=mock.Mock(),
            timeline_service=mock.Mock(),
        )

        today_data = provider.get_today_data()
        active_ticket = today_data["active_work"][0]

        self.assertEqual(active_ticket["linked_promises"][0]["name"], "Daily deep work")
        self.assertEqual(active_ticket["linked_skills"][0]["name"], "Python")
        self.assertEqual(active_ticket["contribution_summary"], "Supports 1 promise and 1 skill")
        self.assertEqual(active_ticket["ticket_code"], "RSB-9")

    def test_today_data_includes_minimal_setup_checklist(self):
        provider = RasbhariDashboardDataProvider(
            project_service=mock.Mock(find_all=mock.Mock(return_value=[]), count=mock.Mock(return_value=1)),
            kanban_ticket_service=mock.Mock(
                get_by_project_id=mock.Mock(return_value=[]),
                count=mock.Mock(return_value=1),
                find_all=mock.Mock(return_value=[]),
            ),
            promise_service=mock.Mock(get_due_promises=mock.Mock(return_value=[]), find_all=mock.Mock(return_value=[]), count=mock.Mock(return_value=0)),
            skill_service=mock.Mock(find_all=mock.Mock(return_value=[]), get_match_keys=mock.Mock(return_value=set()), count=mock.Mock(return_value=1)),
            connection_service=mock.Mock(get_active=mock.Mock(return_value=[])),
            activity_service=mock.Mock(get_recent_items=mock.Mock(return_value=[]), count=mock.Mock(return_value=1)),
            report_service=mock.Mock(get_recent_items=mock.Mock(return_value=[])),
            event_service=mock.Mock(find_all=mock.Mock(return_value=[])),
            notification_service=mock.Mock(),
            device_service=mock.Mock(),
            queue_service=mock.Mock(),
            skill_history_service=mock.Mock(),
            timeline_service=mock.Mock(),
        )

        today_data = provider.get_today_data()
        checklist = today_data["setup_checklist"]

        self.assertEqual(checklist["completed_count"], 4)
        self.assertEqual(checklist["total_count"], 6)
        self.assertFalse(checklist["is_complete"])
        self.assertEqual(checklist["items"][0]["title"], "Create one activity")
        self.assertTrue(checklist["items"][0]["completed"])
        self.assertEqual(checklist["items"][-1]["title"], "Move one ticket forward")
        self.assertFalse(checklist["items"][-1]["completed"])

    def test_today_template_hides_completed_setup_checklist(self):
        app = Flask(__name__, template_folder=os.path.join(BASE_DIR, "templates"))
        app.secret_key = "test-secret"

        with app.test_request_context("/"):
            rendered = render_flask_template(
                "today.html",
                today_data={
                    "guidance": [],
                    "active_work": [],
                    "prioritized_work": [],
                    "due_promises": [],
                    "neglected_connections": [],
                    "suggested_activities": [],
                    "recommended_follow_ups": [],
                    "active_project_count": 0,
                    "latest_report": None,
                    "events_today_count": 0,
                    "setup_checklist": {
                        "title": "Minimal Useful Setup",
                        "summary": "Done.",
                        "items": [],
                        "completed_count": 6,
                        "total_count": 6,
                        "is_complete": True,
                    },
                },
                PermissionManager=mock.Mock(can_view_app=lambda *_: False),
                active_app_names=set(),
                current_user={"id": 1, "username": "tester", "display_name": "Tester", "is_admin": False, "onboarding_completed": True},
                Role=mock.Mock(),
            )

        self.assertNotIn("Minimal Useful Setup", rendered)

    def test_today_data_respects_global_recommendation_limit(self):
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
        user = User(id=1, username="tester", display_name="Tester", recommendation_limit=1, recommendations_enabled=True)
        follow_ups = [
            {"title": "First", "action": "one", "confidence": 0.9},
            {"title": "Second", "action": "two", "confidence": 0.8},
        ]
        provider = RasbhariDashboardDataProvider(
            project_service=mock.Mock(find_all=mock.Mock(return_value=[project]), count=mock.Mock(return_value=0)),
            kanban_ticket_service=mock.Mock(get_by_project_id=mock.Mock(return_value=[]), count=mock.Mock(return_value=0), find_all=mock.Mock(return_value=[])),
            promise_service=mock.Mock(get_due_promises=mock.Mock(return_value=[]), find_all=mock.Mock(return_value=[]), count=mock.Mock(return_value=0)),
            skill_service=mock.Mock(find_all=mock.Mock(return_value=[]), get_match_keys=mock.Mock(return_value=set()), count=mock.Mock(return_value=0)),
            connection_service=mock.Mock(get_active=mock.Mock(return_value=[])),
            activity_service=mock.Mock(get_recent_items=mock.Mock(return_value=[]), count=mock.Mock(return_value=0)),
            report_service=mock.Mock(get_recent_items=mock.Mock(return_value=[])),
            event_service=mock.Mock(find_all=mock.Mock(return_value=[])),
            notification_service=mock.Mock(),
            device_service=mock.Mock(),
            queue_service=mock.Mock(),
            skill_history_service=mock.Mock(),
            timeline_service=mock.Mock(),
            recommendation_followup_service=mock.Mock(get_follow_ups=mock.Mock(return_value=follow_ups)),
            user_service=mock.Mock(get_by_id=mock.Mock(return_value=user)),
        )

        app = Flask(__name__)
        with app.test_request_context("/"), mock.patch("runtime.providers.PermissionManager.get_current_user_id", return_value=1):
            today_data = provider.get_today_data()

        self.assertEqual(len(today_data["recommended_follow_ups"]), 1)
        self.assertEqual(today_data["recommended_follow_ups"][0]["title"], "First")


if __name__ == "__main__":
    unittest.main()
