import os
import unittest
from datetime import datetime, timedelta
from unittest import mock

os.environ.setdefault("LOG_DIR", "/tmp/rasbhari-test-logs")
os.environ.setdefault("FLASK_SECRET_KEY", "test-secret")

from flask import Flask

from apps.promises import PromiseApp
from gabru.auth import PermissionManager
from model.event import Event
from model.promise import Promise


class PromisesAppTests(unittest.TestCase):
    def setUp(self):
        self.app_instance = PromiseApp()
        self.flask_app = Flask(__name__)
        self.flask_app.secret_key = "test-secret"
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


if __name__ == "__main__":
    unittest.main()
