import os
import unittest
from datetime import datetime, timedelta
from unittest import mock
from types import SimpleNamespace

os.environ.setdefault("LOG_DIR", "/tmp/rasbhari-test-logs")
os.environ.setdefault("FLASK_SECRET_KEY", "test-secret")

from flask import Flask

from apps.promises import PromiseApp
from gabru.auth import PermissionManager
from model.event import Event
from model.promise import Promise

BASE_DIR = os.path.dirname(os.path.dirname(__file__))


class PromisesAppTests(unittest.TestCase):
    def setUp(self):
        self.app_instance = PromiseApp()
        self.flask_app = Flask(__name__, template_folder=os.path.join(BASE_DIR, "templates"))
        self.flask_app.secret_key = "test-secret"
        self.flask_app.jinja_env.filters["datetimeformat"] = lambda value: value.strftime("%b %d, %Y, %I:%M %p") if value else ""
        self.flask_app.context_processor(lambda: {
            "PermissionManager": PermissionManager,
            "active_app_names": {"promises"},
            "current_user": {"id": 1, "username": "tester", "display_name": "Tester", "is_admin": False, "onboarding_completed": True},
            "build_info": {"commit": None, "label": ""},
            "open_webui_url": None,
        })
        self.flask_app.register_blueprint(self.app_instance.blueprint, url_prefix="/promises")
        self.client = self.flask_app.test_client()

    def tearDown(self):
        PermissionManager._auth_provider = None

    def test_refresh_stats_counts_project_work_events_for_project_target(self):
        promise = Promise(
            id=4,
            user_id=1,
            name="Advance Rasbhari project",
            description="",
            frequency="daily",
            target_event_type="project:rasbhari",
            required_count=1,
            created_at=datetime.now() - timedelta(days=1),
            updated_at=datetime.now(),
        )
        matching_event = Event(
            id=10,
            user_id=1,
            event_type="kanban:ticket_moved",
            description="Moved ticket",
            timestamp=datetime.now() - timedelta(hours=2),
            tags=["project_work:rasbhari"],
        )
        non_matching_event = Event(
            id=11,
            user_id=1,
            event_type="kanban:ticket_moved",
            description="Moved other ticket",
            timestamp=datetime.now() - timedelta(hours=1),
            tags=["project_work:other-project"],
        )

        with self.client.application.test_request_context():
            with mock.patch.object(PermissionManager, "is_authenticated", return_value=True), \
                 mock.patch.object(PermissionManager, "can_write", return_value=True), \
                 mock.patch.object(PermissionManager, "can_access_route", return_value=True), \
                 mock.patch.object(self.app_instance.service, "get_by_id", return_value=promise), \
                 mock.patch.object(self.app_instance.service, "update", return_value=True) as update_mock, \
                 mock.patch("services.events.EventService") as event_service_cls:
                event_service_cls.return_value.find_all.return_value = [matching_event, non_matching_event]

                response = self.client.post("/promises/4/refresh")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.get_json()["current_count"], 1)
        self.assertEqual(promise.current_count, 1)
        update_mock.assert_called_once()

    def test_home_renders_contextual_recommendations_on_promise_cards(self):
        promise = Promise(
            id=4,
            user_id=1,
            name="Advance Rasbhari project",
            description="",
            frequency="daily",
            target_event_type="work:deep",
            required_count=1,
            created_at=datetime.now() - timedelta(days=1),
            updated_at=datetime.now(),
        )
        recommendation = SimpleNamespace(
            id="promise-link:4:deep-work",
            title="Link promise Advance Rasbhari project to `deep-work`",
            body="Activities already emit `work:deep` with the `deep-work` tag.",
            action="update_promise_target_tag",
            confidence=0.78,
            reasoning="Matching activities consistently carry the suggested tag.",
            payload={"promise_id": 4, "promise_target_event_tag": "deep-work"},
            scope="item",
            scope_id=4,
            app_name="Promises",
            priority=88,
            kind="stage_action",
            action_label="Link Tag",
            tags=["promises", "linking", "deep-work"],
        )

        with self.client.application.test_request_context():
            with mock.patch.object(PermissionManager, "is_authenticated", return_value=True), \
                 mock.patch.object(PermissionManager, "can_access_route", return_value=True), \
                 mock.patch.object(PermissionManager, "get_current_user_id", return_value=1), \
                 mock.patch.object(self.app_instance.service, "get_all", return_value=[promise]), \
                 mock.patch("apps.promises.user_service.get_by_id", return_value=SimpleNamespace(id=1, recommendations_enabled=True, recommendation_limit=2)), \
                 mock.patch(
                     "apps.promises.recommendation_followup_service.recommendation_engine.get_recommendations",
                     return_value=[recommendation],
                 ):
                response = self.client.get("/promises/home")

        self.assertEqual(response.status_code, 200)
        rendered = response.get_data(as_text=True)
        self.assertIn("Recommendations", rendered)
        self.assertIn("Link promise Advance Rasbhari project to", rendered)
        self.assertIn("Link Tag", rendered)


if __name__ == "__main__":
    unittest.main()
