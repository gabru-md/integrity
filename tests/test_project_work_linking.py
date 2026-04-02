import os
import unittest
from datetime import datetime
from unittest import mock

os.environ.setdefault("LOG_DIR", "/tmp/rasbhari-test-logs")

from model.kanban_ticket import KanbanTicket
from model.project import Project, ProjectState
from model.promise import Promise
from model.skill import Skill
from runtime.providers import RasbhariDashboardDataProvider
from services.kanban_tickets import KanbanTicketService


class ProjectWorkLinkingTests(unittest.TestCase):
    def test_kanban_event_tags_include_project_work_and_focus_tags(self):
        project = Project(
            id=3,
            user_id=1,
            name="Rasbhari",
            project_type="Code",
            focus_tags=["python", "deep-work"],
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
            start_date=datetime(2026, 4, 2, 9, 0, 0),
            state=ProjectState.ACTIVE,
        )
        ticket = KanbanTicket(
            id=9,
            user_id=1,
            project_id=3,
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
            project_service=mock.Mock(find_all=mock.Mock(return_value=[project])),
            kanban_ticket_service=mock.Mock(get_by_project_id=mock.Mock(return_value=[ticket])),
            promise_service=mock.Mock(get_due_promises=mock.Mock(return_value=[]), find_all=mock.Mock(return_value=[promise])),
            skill_service=mock.Mock(find_all=mock.Mock(return_value=[skill]), get_match_keys=mock.Mock(return_value={"python"})),
            connection_service=mock.Mock(get_active=mock.Mock(return_value=[])),
            activity_service=mock.Mock(get_recent_items=mock.Mock(return_value=[])),
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


if __name__ == "__main__":
    unittest.main()
