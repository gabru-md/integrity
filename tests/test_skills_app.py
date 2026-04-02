import os
import unittest
from types import SimpleNamespace
from unittest import mock

from flask import Flask

os.environ.setdefault("LOG_DIR", "/tmp/rasbhari-test-logs")
os.environ.setdefault("FLASK_SECRET_KEY", "test-secret")

from apps.skills import skills_app
from gabru.auth import PermissionManager


class SkillsAppTests(unittest.TestCase):
    def _build_client(self):
        flask_app = Flask(__name__)
        flask_app.secret_key = "test-secret"
        flask_app.register_blueprint(skills_app.blueprint, url_prefix="/skills")
        return flask_app.test_client()

    def test_recommendations_route_returns_skill_recommendation_map(self):
        client = self._build_client()
        recommendation = SimpleNamespace(
            id="skill-signal:4",
            title="Connect Python more explicitly",
            body="Python already has matching signal in 1 activity and 1 active project.",
            action=None,
            confidence=0.74,
            reasoning="Matching activities or active projects already carry tags that align with this skill.",
            payload={},
            scope="item",
            scope_id=4,
            app_name="Skills",
            priority=72,
            kind="info",
            action_label=None,
            tags=["skills", "linking", "python"],
        )

        with mock.patch.object(PermissionManager, "is_authenticated", return_value=True), \
             mock.patch.object(PermissionManager, "can_access_route", return_value=True), \
             mock.patch.object(PermissionManager, "get_current_user_id", return_value=1), \
             mock.patch("apps.skills.skills_app.user_service.get_by_id", return_value=SimpleNamespace(id=1, recommendations_enabled=True, recommendation_limit=2)), \
             mock.patch(
                 "apps.skills.skills_app.recommendation_followup_service.recommendation_engine.get_recommendations",
                 return_value=[recommendation],
             ):
            response = client.get("/skills/recommendations")

        self.assertEqual(response.status_code, 200)
        payload = response.get_json()
        self.assertIn("4", payload)
        self.assertEqual(payload["4"][0]["title"], "Connect Python more explicitly")
        self.assertEqual(payload["4"][0]["kind"], "info")


if __name__ == "__main__":
    unittest.main()
