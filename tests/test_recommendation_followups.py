import os
import unittest
from datetime import datetime, timedelta

os.environ.setdefault("LOG_DIR", "/tmp/rasbhari-test-logs")

from model.project import Project, ProjectState
from model.activity import Activity
from model.promise import Promise
from model.skill import Skill
from services.assistant_command import AssistantCommandService
from services.recommendation_engine import RecommendationEngineService
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

    def get_by_id(self, entity_id):
        return next((promise for promise in self.promises if promise.id == entity_id), None)

    def update(self, promise):
        for index, existing in enumerate(self.promises):
            if existing.id == promise.id:
                self.promises[index] = promise
                return True
        return False


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
    def __init__(self, activities=None):
        self.activities = list(activities or [])

    def find_all(self, filters=None, sort_by=None):
        return list(self.activities)

    def get_by_id(self, entity_id):
        return next((activity for activity in self.activities if activity.id == entity_id), None)

    def update(self, activity):
        for index, existing in enumerate(self.activities):
            if existing.id == activity.id:
                self.activities[index] = activity
                return True
        return False


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

    def test_followups_include_deterministic_link_recommendations(self):
        promise = Promise(
            id=11,
            user_id=7,
            name="Keep Amazon orders visible",
            frequency="daily",
            target_event_type="amazon:order",
            target_event_tag=None,
        )
        activity = Activity(
            id=5,
            user_id=7,
            name="Amazon Order",
            event_type="amazon:order",
            tags=["amazon"],
        )
        skill = Skill(id=4, user_id=7, name="Amazon Ops", tag_key="amazon", aliases=[])
        service = RecommendationFollowUpService(
            project_service=FakeProjectService([]),
            kanban_ticket_service=FakeKanbanTicketService(),
            promise_service=FakePromiseService([promise]),
            skill_service=FakeSkillService([skill]),
            activity_service=FakeActivityService([activity]),
        )

        items = service.get_follow_ups(user_id=7, limit=6)
        actions = [item["action"] for item in items]

        self.assertIn("update_promise_target_tag", actions)

    def test_engine_emits_ranked_structured_recommendations(self):
        project = Project(
            id=3,
            user_id=7,
            name="Rasbhari",
            project_type="Code",
            focus_tags=["python"],
            start_date=datetime(2026, 4, 1, 9, 0, 0),
            state=ProjectState.ACTIVE,
            last_updated=datetime.now() - timedelta(days=10),
        )
        promise = Promise(
            id=11,
            user_id=7,
            name="Keep Amazon orders visible",
            frequency="daily",
            target_event_type="amazon:order",
            target_event_tag=None,
        )
        activity = Activity(
            id=5,
            user_id=7,
            name="Amazon Order",
            event_type="amazon:order",
            tags=["amazon"],
        )
        engine = RecommendationEngineService(
            project_service=FakeProjectService([project]),
            kanban_ticket_service=FakeKanbanTicketService(),
            promise_service=FakePromiseService([promise]),
            skill_service=FakeSkillService(),
            activity_service=FakeActivityService([activity]),
        )

        items = engine.get_recommendations(user_id=7, limit=6)

        self.assertTrue(items)
        self.assertGreaterEqual(items[0].priority, items[-1].priority)
        self.assertEqual(items[0].app_name, "Promises")
        self.assertEqual(items[0].scope, "item")
        self.assertIsNotNone(items[0].action)
        self.assertTrue(items[0].reasoning)

    def test_engine_emits_skill_signal_recommendations(self):
        project = Project(
            id=3,
            user_id=7,
            name="Rasbhari",
            project_type="Code",
            focus_tags=["python"],
            start_date=datetime(2026, 4, 1, 9, 0, 0),
            state=ProjectState.ACTIVE,
            last_updated=datetime.now(),
        )
        activity = Activity(
            id=5,
            user_id=7,
            name="Python Session",
            event_type="work:python",
            tags=["python"],
        )
        skill = Skill(id=4, user_id=7, name="Python", tag_key="python", aliases=[])
        engine = RecommendationEngineService(
            project_service=FakeProjectService([project]),
            kanban_ticket_service=FakeKanbanTicketService(),
            promise_service=FakePromiseService(),
            skill_service=FakeSkillService([skill]),
            activity_service=FakeActivityService([activity]),
        )

        items = engine.get_recommendations(user_id=7, app_name="Skills", limit=4)

        self.assertEqual(len(items), 1)
        self.assertEqual(items[0].app_name, "Skills")
        self.assertEqual(items[0].scope_id, 4)
        self.assertEqual(items[0].kind, "info")
        self.assertIn("matching signal", items[0].body)


class RecommendationActionBridgeTests(unittest.TestCase):
    def setUp(self):
        self.skill_service = FakeSkillService()
        self.ticket_service = FakeKanbanTicketService()
        self.promise_service = FakePromiseService()
        self.project_update_service = FakeProjectUpdateService()
        self.activity_service = FakeActivityService()
        self.service = AssistantCommandService(
            event_service=FakeEventService(),
            activity_service=self.activity_service,
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

    def test_recommendation_can_link_promise_tag(self):
        promise = Promise(
            id=9,
            user_id=7,
            name="Keep Amazon orders visible",
            frequency="daily",
            target_event_type="amazon:order",
            target_event_tag=None,
        )
        self.promise_service.promises.append(promise)
        recommendation = {
            "title": "Link promise Keep Amazon orders visible to `amazon`",
            "body": "Matching activities already emit the amazon tag.",
            "action": "update_promise_target_tag",
            "confidence": 0.78,
            "reasoning": "Matching event types already carry the suggested tag.",
            "payload": {
                "promise_id": 9,
                "promise_target_event_type": "amazon:order",
                "promise_target_event_tag": "amazon",
            },
        }

        staged = self.service.handle_recommendation(user_id=7, recommendation=recommendation)
        self.assertTrue(staged.requires_confirmation)
        confirmed = self.service.handle(user_id=7, message="yes", confirm=True)
        self.assertTrue(confirmed.executed)
        self.assertEqual(self.promise_service.promises[0].target_event_tag, "amazon")

    def test_recommendation_can_append_activity_tag(self):
        activity = Activity(
            id=12,
            user_id=7,
            name="Amazon Order",
            event_type="amazon:order",
            tags=[],
        )
        self.activity_service.activities.append(activity)
        recommendation = {
            "title": "Add `amazon` to Amazon Order",
            "body": "The activity already looks like amazon work.",
            "action": "append_activity_tags",
            "confidence": 0.76,
            "reasoning": "The activity name matches an existing ecosystem tag.",
            "payload": {
                "activity_id": 12,
                "activity_name": "Amazon Order",
                "activity_tag_updates": ["amazon"],
            },
        }

        staged = self.service.handle_recommendation(user_id=7, recommendation=recommendation)
        self.assertTrue(staged.requires_confirmation)
        confirmed = self.service.handle(user_id=7, message="yes", confirm=True)
        self.assertTrue(confirmed.executed)
        self.assertIn("amazon", self.activity_service.activities[0].tags)


if __name__ == "__main__":
    unittest.main()
