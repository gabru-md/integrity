import os
import unittest
from unittest import mock
from types import SimpleNamespace

from flask import Flask

os.environ.setdefault("LOG_DIR", "/tmp/rasbhari-test-logs")
os.environ.setdefault("FLASK_SECRET_KEY", "test-secret")

from apps.activities import activities_app
from gabru.auth import PermissionManager


class ActivitiesAppTests(unittest.TestCase):
    def _build_client(self):
        flask_app = Flask(__name__)
        flask_app.secret_key = "test-secret"
        flask_app.register_blueprint(activities_app.blueprint, url_prefix="/activities")
        return flask_app.test_client()

    def test_catalog_route_returns_enriched_activities(self):
        client = self._build_client()
        activity = SimpleNamespace(
            id=1,
            name="Deep Work",
            event_type="work:deep",
            description="Focus block",
            tags=["deep-work", "python"],
            default_payload={},
            dict=lambda: {
                "id": 1,
                "name": "Deep Work",
                "event_type": "work:deep",
                "description": "Focus block",
                "tags": ["deep-work", "python"],
                "default_payload": {},
            },
        )

        latest_event = mock.Mock()
        latest_event.dict.return_value = {
            "event_type": "work:deep",
            "description": "Triggered",
            "timestamp": "2026-04-02T12:00:00",
            "tags": ["deep-work", "python"],
        }

        promise = SimpleNamespace(id=4, name="Daily deep work", target_event_type=None, target_event_tag="deep-work")
        skill = SimpleNamespace(id=8, name="Python", tag_key="python", aliases=[])

        with mock.patch.object(PermissionManager, "is_authenticated", return_value=True), \
             mock.patch.object(PermissionManager, "get_current_user_id", return_value=1), \
             mock.patch.object(PermissionManager, "can_access_route", return_value=True), \
             mock.patch("apps.activities.activity_service.find_all", return_value=[activity]), \
             mock.patch("apps.activities.event_service.find_all", return_value=[latest_event]), \
             mock.patch("apps.activities.promise_service.find_all", return_value=[promise]), \
             mock.patch("apps.activities.skill_service.find_all", return_value=[skill]), \
             mock.patch("apps.activities.skill_service.get_match_keys", return_value={"python"}), \
             mock.patch("apps.activities.user_service.get_by_id", return_value=SimpleNamespace(id=1, recommendations_enabled=True, recommendation_limit=2)), \
             mock.patch(
                 "apps.activities.recommendation_followup_service.recommendation_engine.get_recommendations",
                 return_value=[
                     SimpleNamespace(
                         id="activity-link:1:deep-work",
                         title="Add `deep-work` to Deep Work",
                         body="Deep Work already reads like deep work, but the activity is not tagged that way yet.",
                         action="append_activity_tags",
                         confidence=0.76,
                         reasoning="The activity name matches an existing promise or skill tag.",
                         payload={"activity_id": 1, "activity_tag_updates": ["deep-work"]},
                         scope="item",
                         scope_id=1,
                         app_name="Activities",
                         priority=84,
                         kind="stage_action",
                         action_label="Add Tag",
                         tags=["activities", "linking", "deep-work"],
                     )
                 ],
             ):
            response = client.get("/activities/catalog")

        self.assertEqual(response.status_code, 200)
        payload = response.get_json()
        self.assertEqual(payload[0]["event_summary"], "work:deep · 2 tags")
        self.assertEqual(payload[0]["linked_promises"][0]["name"], "Daily deep work")
        self.assertEqual(payload[0]["linked_skills"][0]["name"], "Python")
        self.assertEqual(payload[0]["latest_event"]["event_type"], "work:deep")
        self.assertEqual(payload[0]["recommendations"][0]["action"], "append_activity_tags")
        self.assertEqual(payload[0]["recommendations"][0]["action_label"], "Add Tag")


if __name__ == "__main__":
    unittest.main()
