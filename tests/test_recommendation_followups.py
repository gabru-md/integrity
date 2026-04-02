import os
import unittest
from datetime import datetime, timedelta

os.environ.setdefault("LOG_DIR", "/tmp/rasbhari-test-logs")

from model.project import Project, ProjectState
from model.promise import Promise
from model.skill import Skill
from services.assistant_command import AssistantCommandService
from services.recommendation_followups import RecommendationFollowUpService


class FakeProjectService:
    def __init__(self, projects):
        self.projects = projects

    def find_all(self, filters=None, sort_by=None):
        return list(self.projects)


class FakeKanbanTicketService:
    def __init__(self):
        self.created = []

    def get_by_project_id(self, project_id, include_archived=False):
        return []

    def create(self, ticket):
        self.created.append(ticket)
        return len(self.created)


class FakePromiseService:
    def __init__(self, promises=None):
        self.promises = list(promises or [])
        self.created = []

    def find_all(self, filters=None, sort_by=None):
        return list(self.promises)

    def create(self, promise):
        self.created.append(promise)
        return len(self.created)


class FakeSkillService:
    def __init__(self, skills=None):
        self.skills = list(skills or [])
        self.created = []

    def find_all(self, filters=None, sort_by=None):
        return list(self.skills)

    def create(self, skill):
        self.created.append(skill)
        return len(self.created)

    def get_match_keys(self, skill):
        candidates = [skill.tag_key or skill.name, skill.name, *(skill.aliases or [])]
        return {self.normalize_skill_tag(value) for value in candidates if self.normalize_skill_tag(value)}

    @staticmethod
    def normalize_skill_tag(value):
        value = value.strip().lower().lstrip("#")
        return "".join(char for char in value if char.isalnum())


class FakeEventService:
    def create(self, event):
        return 1


class FakeActivityService:
    def find_all(self, filters=None, sort_by=None):
        return []


class FakeThoughtService:
    def create(self, thought):
        return 1


class FakeProjectUpdateService:
    def __init__(self):
        self.created = []

    def create_update(self, **kwargs):
        self.created.append(kwargs)
        return len(self.created)


class RecommendationFollowUpServiceTests(unittest.TestCase):
    def test_followups_include_skill_ticket_promise_and_update(self):
        project = Project(
            id=3,
            user_id=7,
            name="Rasbhari",
            project_type="Code",
            focus_tags=["python", "deep-work"],
            start_date=datetime(2026, 4, 1, 9, 0, 0),
            state=ProjectState.ACTIVE,
            last_updated=datetime.now() - timedelta(days=10),
        )
        service = RecommendationFollowUpService(
            project_service=FakeProjectService([project]),
            kanban_ticket_service=FakeKanbanTicketService(),
            promise_service=FakePromiseService(),
            skill_service=FakeSkillService(),
        )

        items = service.get_follow_ups(user_id=7, limit=4)
        actions = [item["action"] for item in items]

        self.assertIn("create_skill", actions)
        self.assertIn("create_promise", actions)
        self.assertIn("create_ticket", actions)
        self.assertIn("create_project_update", actions)


class RecommendationActionBridgeTests(unittest.TestCase):
    def setUp(self):
        self.skill_service = FakeSkillService()
        self.ticket_service = FakeKanbanTicketService()
        self.promise_service = FakePromiseService()
        self.project_update_service = FakeProjectUpdateService()
        self.service = AssistantCommandService(
            event_service=FakeEventService(),
            activity_service=FakeActivityService(),
            thought_service=FakeThoughtService(),
            promise_service=self.promise_service,
            skill_service=self.skill_service,
            kanban_ticket_service=self.ticket_service,
            project_update_service=self.project_update_service,
            ollama_url="http://ollama.local",
            model_name="test-model",
            timeout_seconds=1,
        )

    def test_recommendation_is_staged_then_creates_skill_on_confirm(self):
        recommendation = {
            "title": "Create skill for python",
            "body": "Turn project work into visible growth.",
            "action": "create_skill",
            "confidence": 0.82,
            "reasoning": "Project focus tags already use python.",
            "payload": {
                "skill_name": "Python",
                "skill_tag_key": "python",
                "skill_aliases": ["py"],
            },
        }

        staged = self.service.handle_recommendation(user_id=7, recommendation=recommendation)
        self.assertTrue(staged.requires_confirmation)
        self.assertEqual(staged.action, "create_skill")

        confirmed = self.service.handle(user_id=7, message="yes", confirm=True)
        self.assertTrue(confirmed.executed)
        self.assertEqual(self.skill_service.created[0].name, "Python")

    def test_recommendation_can_create_ticket(self):
        recommendation = {
            "title": "Create next ticket",
            "body": "The board needs one concrete next step.",
            "action": "create_ticket",
            "confidence": 0.69,
            "reasoning": "No active tickets exist.",
            "payload": {
                "ticket_project_id": 3,
                "ticket_title": "Define next step for Rasbhari",
                "ticket_description": "Capture the next unit of work.",
                "ticket_state": "backlog",
            },
        }

        staged = self.service.handle_recommendation(user_id=7, recommendation=recommendation)
        self.assertTrue(staged.requires_confirmation)
        confirmed = self.service.handle(user_id=7, message="yes", confirm=True)
        self.assertTrue(confirmed.executed)
        self.assertEqual(self.ticket_service.created[0].project_id, 3)


if __name__ == "__main__":
    unittest.main()
