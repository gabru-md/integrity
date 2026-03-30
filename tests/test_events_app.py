import os
import unittest
from unittest import mock

from flask import Flask

os.environ.setdefault("LOG_DIR", "/tmp/rasbhari-test-logs")
os.environ.setdefault("FLASK_SECRET_KEY", "test-secret")

from apps.events import events_app
from gabru.auth import PermissionManager


class EventsAppRequestParsingTests(unittest.TestCase):
    def _build_client(self):
        flask_app = Flask(__name__)
        flask_app.secret_key = "test-secret"
        flask_app.register_blueprint(events_app.blueprint, url_prefix="/events")
        return flask_app.test_client()

    def test_create_accepts_json_tag_list(self):
        client = self._build_client()
        with mock.patch.object(PermissionManager, "is_authenticated", return_value=True), \
             mock.patch.object(PermissionManager, "can_write", return_value=True), \
             mock.patch.object(PermissionManager, "can_access_route", return_value=True), \
             mock.patch.object(events_app.service, "create", return_value=1) as create_mock:
            response = client.post(
                "/events/",
                json={
                    "event_type": "mac:activity",
                    "description": "Opened PyCharm",
                    "tags": ["source:mac_agent", "app:pycharm", "machine:gabru-md-home"],
                },
            )

        self.assertEqual(response.status_code, 200)
        created_event = create_mock.call_args.args[0]
        self.assertEqual(created_event.tags, ["source:mac_agent", "app:pycharm", "machine:gabru-md-home"])

    def test_create_accepts_comma_separated_tag_string(self):
        client = self._build_client()
        with mock.patch.object(PermissionManager, "is_authenticated", return_value=True), \
             mock.patch.object(PermissionManager, "can_write", return_value=True), \
             mock.patch.object(PermissionManager, "can_access_route", return_value=True), \
             mock.patch.object(events_app.service, "create", return_value=1) as create_mock:
            response = client.post(
                "/events/",
                json={
                    "event_type": "mac:activity",
                    "description": "Opened PyCharm",
                    "tags": "source:mac_agent, app:pycharm, machine:gabru-md-home",
                },
            )

        self.assertEqual(response.status_code, 200)
        created_event = create_mock.call_args.args[0]
        self.assertEqual(created_event.tags, ["source:mac_agent", "app:pycharm", "machine:gabru-md-home"])


if __name__ == "__main__":
    unittest.main()
