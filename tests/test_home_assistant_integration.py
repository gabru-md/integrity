import os
import unittest
from unittest import mock

from flask import Flask

os.environ.setdefault("LOG_DIR", "/tmp/rasbhari-test-logs")
os.environ.setdefault("FLASK_SECRET_KEY", "test-secret")

from apps.home_assistant import home_assistant_blueprint
from gabru.auth import PermissionManager


class HomeAssistantIntegrationTests(unittest.TestCase):
    def _build_client(self):
        flask_app = Flask(__name__)
        flask_app.secret_key = "test-secret"
        flask_app.register_blueprint(home_assistant_blueprint)
        return flask_app.test_client()

    def test_ingest_event_creates_enriched_rasbhari_event(self):
        client = self._build_client()
        with mock.patch.object(PermissionManager, "is_authenticated", return_value=True), \
             mock.patch.object(PermissionManager, "get_current_user_id", return_value=42), \
             mock.patch("apps.home_assistant.event_service.create", return_value=123) as create_mock:
            response = client.post(
                "/integrations/home-assistant/events",
                headers={"X-API-Key": "abcde"},
                json={
                    "event_type": "home:litterbox_cleaned",
                    "description": "Litterbox was cleaned",
                    "tags": ["cat", "litterbox"],
                    "payload": {"entity_id": "binary_sensor.litterbox_cleaned"},
                },
            )

        self.assertEqual(response.status_code, 201)
        created_event = create_mock.call_args.args[0]
        self.assertEqual(created_event.user_id, 42)
        self.assertEqual(created_event.event_type, "home:litterbox_cleaned")
        self.assertEqual(created_event.description, "Litterbox was cleaned")
        self.assertEqual(
            created_event.tags,
            ["cat", "litterbox", "home", "source:home_assistant", "integration:home_assistant"],
        )
        self.assertEqual(created_event.payload["entity_id"], "binary_sensor.litterbox_cleaned")
        self.assertEqual(created_event.payload["source"], "home_assistant")
        self.assertEqual(response.get_json()["id"], 123)

    def test_ingest_event_rejects_missing_event_type(self):
        client = self._build_client()
        with mock.patch.object(PermissionManager, "is_authenticated", return_value=True), \
             mock.patch.object(PermissionManager, "get_current_user_id", return_value=42), \
             mock.patch("apps.home_assistant.event_service.create") as create_mock:
            response = client.post(
                "/integrations/home-assistant/events",
                json={"description": "No type"},
            )

        self.assertEqual(response.status_code, 400)
        create_mock.assert_not_called()


if __name__ == "__main__":
    unittest.main()
