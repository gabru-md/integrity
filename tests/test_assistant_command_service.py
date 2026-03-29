import json
import os
import unittest
from unittest import mock

os.environ.setdefault("LOG_DIR", "/tmp/rasbhari-test-logs")

from model.activity import Activity
from model.event import Event
from services.assistant_command import AssistantCommandService


class FakeHTTPResponse:
    def __init__(self, body):
        self.body = body

    def read(self):
        return self.body

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        return False


class FakeEventService:
    def __init__(self):
        self.created = []

    def create(self, event):
        self.created.append(event)
        return len(self.created)


class FakeActivityService:
    def __init__(self):
        self.activities = [
            Activity(
                id=3,
                user_id=7,
                name="Litterbox Cleaned",
                event_type="litterbox:cleaned",
                description="Litter box cleaned",
                tags=["cleaning"],
            )
        ]
        self.triggered = []

    def find_all(self, filters=None, sort_by=None):
        user_id = (filters or {}).get("user_id")
        if user_id is None:
            return list(self.activities)
        return [activity for activity in self.activities if activity.user_id == user_id]

    def trigger_activity(self, activity_id, override_payload=None):
        self.triggered.append((activity_id, override_payload))
        return activity_id


class FakeThoughtService:
    def __init__(self):
        self.created = []

    def create(self, thought):
        self.created.append(thought)
        return len(self.created)


class FakePromiseService:
    def __init__(self):
        self.created = []
        self.promises = []

    def find_all(self, filters=None, sort_by=None):
        return list(self.promises)

    def create(self, promise):
        self.created.append(promise)
        return len(self.created)


class FakeSkillService:
    def find_all(self, filters=None, sort_by=None):
        return []


class AssistantCommandServiceTests(unittest.TestCase):
    def setUp(self):
        self.event_service = FakeEventService()
        self.activity_service = FakeActivityService()
        self.thought_service = FakeThoughtService()
        self.promise_service = FakePromiseService()
        self.skill_service = FakeSkillService()
        self.service = AssistantCommandService(
            event_service=self.event_service,
            activity_service=self.activity_service,
            thought_service=self.thought_service,
            promise_service=self.promise_service,
            skill_service=self.skill_service,
            ollama_url="http://ollama.local",
            model_name="test-model",
            timeout_seconds=1,
        )

    def test_create_event_stages_until_confirmed(self):
        body = json.dumps(
            {
                "message": {
                    "content": json.dumps(
                        {
                            "action": "create_event",
                            "confidence": 0.84,
                            "reasoning": "The user is clearly reporting a reading session.",
                            "summary": "Create reading event.",
                            "event_type": "article:read",
                            "description": "Read an article about Raspberry Pi tooling",
                            "tags": ["reading", "learning"],
                            "response": "Logged reading session.",
                        }
                    )
                }
            }
        ).encode("utf-8")

        with mock.patch("urllib.request.urlopen", return_value=FakeHTTPResponse(body)):
            result = self.service.handle(user_id=7, message="I read an article about Raspberry Pi tooling")

        self.assertTrue(result.ok)
        self.assertFalse(result.executed)
        self.assertTrue(result.requires_confirmation)
        self.assertEqual(result.action, "create_event")
        self.assertEqual(len(self.event_service.created), 0)

        confirmed = self.service.handle(user_id=7, message="yes")
        self.assertTrue(confirmed.ok)
        self.assertTrue(confirmed.executed)
        self.assertEqual(len(self.event_service.created), 1)
        self.assertEqual(self.event_service.created[0].event_type, "article:read")
        self.assertIn("learning", self.event_service.created[0].tags)

    def test_create_promise_requires_confirmation_when_confidence_is_low(self):
        body = json.dumps(
            {
                "message": {
                    "content": json.dumps(
                        {
                            "action": "create_promise",
                            "confidence": 0.64,
                            "reasoning": "The user seems to be creating a recurring commitment.",
                            "summary": "Create a daily litter box promise.",
                            "promise_name": "Clean litter box",
                            "promise_description": "Keep Cosmo's litter box clean.",
                            "promise_frequency": "daily",
                            "promise_target_event_type": "litterbox:cleaned",
                            "promise_target_event_tag": "cleaning",
                            "promise_required_count": 1,
                            "response": "I can create that promise once you confirm.",
                        }
                    )
                }
            }
        ).encode("utf-8")

        with mock.patch("urllib.request.urlopen", return_value=FakeHTTPResponse(body)):
            result = self.service.handle(user_id=7, message="Remind me to clean the litter box daily")

        self.assertTrue(result.ok)
        self.assertFalse(result.executed)
        self.assertTrue(result.requires_confirmation)
        self.assertEqual(len(self.promise_service.created), 0)

    def test_confirm_executes_trigger_activity(self):
        body = json.dumps(
            {
                "message": {
                    "content": json.dumps(
                        {
                            "action": "trigger_activity",
                            "confidence": 0.42,
                            "reasoning": "There is a direct matching activity.",
                            "summary": "Trigger litterbox activity.",
                            "activity_id": 3,
                            "activity_name": "Litterbox Cleaned",
                            "description": "Cosmo litterbox is cleaned",
                            "tags": ["cleaning"],
                            "response": "I can trigger the litterbox activity.",
                        }
                    )
                }
            }
        ).encode("utf-8")

        with mock.patch("urllib.request.urlopen", return_value=FakeHTTPResponse(body)):
            result = self.service.handle(user_id=7, message="Cosmo litterbox is cleaned")

        self.assertTrue(result.ok)
        self.assertFalse(result.executed)
        self.assertTrue(result.requires_confirmation)
        self.assertEqual(result.action, "trigger_activity")

        result = self.service.handle(user_id=7, message="yes", confirm=True)
        self.assertTrue(result.ok)
        self.assertTrue(result.executed)
        self.assertEqual(self.activity_service.triggered[0][0], 3)

    def test_existing_activity_overrides_raw_event_creation(self):
        body = json.dumps(
            {
                "message": {
                    "content": json.dumps(
                        {
                            "action": "create_event",
                            "confidence": 0.81,
                            "reasoning": "The user reported playing Counter Strike.",
                            "summary": "Create gameplay report event.",
                            "event_type": "report",
                            "description": "User played counter strike with friends for 1 hour",
                            "tags": ["gaming", "friends"],
                            "response": "Logged game session.",
                        }
                    )
                }
            }
        ).encode("utf-8")
        self.activity_service.activities.append(
            Activity(
                id=9,
                user_id=7,
                name="Counter Strike Session",
                event_type="gaming:cs2",
                description="Played Counter Strike",
                tags=["gaming", "counter", "friends"],
            )
        )

        with mock.patch("urllib.request.urlopen", return_value=FakeHTTPResponse(body)):
            result = self.service.handle(user_id=7, message="I played counter strike with friends for 1 hour")

        self.assertTrue(result.ok)
        self.assertFalse(result.executed)
        self.assertTrue(result.requires_confirmation)
        self.assertEqual(result.action, "trigger_activity")
        self.assertEqual(len(self.activity_service.triggered), 0)
        self.assertEqual(len(self.event_service.created), 0)

        confirmed = self.service.handle(user_id=7, message="thanks")
        self.assertTrue(confirmed.ok)
        self.assertTrue(confirmed.executed)
        self.assertEqual(self.activity_service.triggered[0][0], 9)

    def test_nested_response_object_is_normalized(self):
        body = json.dumps(
            {
                "message": {
                    "content": json.dumps(
                        {
                            "action": "create_event",
                            "confidence": 0.8,
                            "reasoning": "The user completed a reading activity.",
                            "summary": "Create reading event.",
                            "event_type": "article:read",
                            "description": "Read an article about postgres connection pooling",
                            "tags": ["reading"],
                            "response": {
                                "answer": "You read an article about postgres connection pooling."
                            },
                        }
                    )
                }
            }
        ).encode("utf-8")

        with mock.patch("urllib.request.urlopen", return_value=FakeHTTPResponse(body)):
            result = self.service.handle(user_id=7, message="I read an article about postgres connection pooling")

        self.assertTrue(result.ok)
        self.assertIn("Planned action", result.response)
        self.assertIn("Event type: article:read", result.response)
        self.assertIn("Confidence: 0.80", result.response)

    def test_invalid_action_string_is_coerced_to_create_thought(self):
        body = json.dumps(
            {
                "message": {
                    "content": json.dumps(
                        {
                            "action": "note that I need to order more cat litter",
                            "confidence": 0.77,
                            "reasoning": "The user is clearly asking to save a note.",
                            "summary": "Create a thought.",
                            "thought_message": "I need to order more cat litter",
                            "response": "Saved your note.",
                        }
                    )
                }
            }
        ).encode("utf-8")

        with mock.patch("urllib.request.urlopen", return_value=FakeHTTPResponse(body)):
            result = self.service.handle(user_id=7, message="note that I need to order more cat litter")

        self.assertTrue(result.ok)
        self.assertFalse(result.executed)
        self.assertTrue(result.requires_confirmation)
        self.assertEqual(result.action, "create_thought")

        confirmed = self.service.handle(user_id=7, message="confirm")
        self.assertTrue(confirmed.ok)
        self.assertTrue(confirmed.executed)

    def test_promise_shaped_payload_overrides_wrong_activity_action(self):
        body = json.dumps(
            {
                "message": {
                    "content": json.dumps(
                        {
                            "action": "trigger_activity",
                            "confidence": 0.8,
                            "reasoning": "The user wants to create a weekly promise called Call Mom with target event type call:mom.",
                            "summary": "Create a new weekly promise for the user.",
                            "event_type": "promise",
                            "description": "Create a weekly promise for the user.",
                            "promise_frequency": "weekly",
                            "promise_name": "Call Mom",
                            "promise_required_count": 1,
                            "promise_target_event_type": "call:mom",
                            "response": "Created promise Call Mom.",
                        }
                    )
                }
            }
        ).encode("utf-8")

        with mock.patch("urllib.request.urlopen", return_value=FakeHTTPResponse(body)):
            result = self.service.handle(user_id=7, message="create a weekly promise called Call Mom with target event type call:mom")

        self.assertTrue(result.ok)
        self.assertFalse(result.executed)
        self.assertTrue(result.requires_confirmation)
        self.assertEqual(result.action, "create_promise")
        self.assertEqual(len(self.promise_service.created), 0)

        confirmed = self.service.handle(user_id=7, message="yes")
        self.assertTrue(confirmed.ok)
        self.assertTrue(confirmed.executed)
        self.assertEqual(len(self.promise_service.created), 1)

    def test_pending_action_must_be_confirmed_or_ignored_before_new_command(self):
        body = json.dumps(
            {
                "message": {
                    "content": json.dumps(
                        {
                            "action": "create_event",
                            "confidence": 0.84,
                            "reasoning": "The user is clearly reporting a reading session.",
                            "summary": "Create reading event.",
                            "event_type": "article:read",
                            "description": "Read an article about Raspberry Pi tooling",
                            "tags": ["reading", "learning"],
                            "response": "Logged reading session.",
                        }
                    )
                }
            }
        ).encode("utf-8")

        with mock.patch("urllib.request.urlopen", return_value=FakeHTTPResponse(body)):
            first = self.service.handle(user_id=7, message="I read an article about Raspberry Pi tooling")

        self.assertTrue(first.requires_confirmation)
        blocked = self.service.handle(user_id=7, message="note that I need to order more cat litter")
        self.assertTrue(blocked.requires_confirmation)
        self.assertIn("already a staged action", blocked.response)
        self.assertEqual(len(self.event_service.created), 0)

        ignored = self.service.handle(user_id=7, message="", cancel=True)
        self.assertTrue(ignored.ok)
        self.assertFalse(ignored.requires_confirmation)
        self.assertIn("Ignored", ignored.response)

    def test_pending_action_can_be_restaged_to_another_action(self):
        body = json.dumps(
            {
                "message": {
                    "content": json.dumps(
                        {
                            "action": "create_event",
                            "confidence": 0.84,
                            "reasoning": "The user is clearly reporting a reading session.",
                            "summary": "Create reading event.",
                            "event_type": "article:read",
                            "description": "Read an article about Raspberry Pi tooling",
                            "tags": ["reading", "learning"],
                            "response": "Logged reading session.",
                        }
                    )
                }
            }
        ).encode("utf-8")

        with mock.patch("urllib.request.urlopen", return_value=FakeHTTPResponse(body)):
            first = self.service.handle(user_id=7, message="I read an article about Raspberry Pi tooling")

        self.assertTrue(first.requires_confirmation)
        changed = self.service.handle(user_id=7, message="", change_action="create_thought")
        self.assertTrue(changed.ok)
        self.assertTrue(changed.requires_confirmation)
        self.assertEqual(changed.action, "create_thought")
        self.assertEqual(changed.payload["thought_message"], "Read an article about Raspberry Pi tooling")
        self.assertEqual(len(self.event_service.created), 0)


if __name__ == "__main__":
    unittest.main()
