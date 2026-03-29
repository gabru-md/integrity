import os
import unittest
from unittest import mock
from typing import Optional

from flask import Flask
from pydantic import Field

os.environ.setdefault("LOG_DIR", "/tmp/rasbhari-test-logs")
os.environ.setdefault("FLASK_SECRET_KEY", "test-secret")

from gabru.auth import PermissionManager
from gabru.flask.app import App
from gabru.flask.server import Server
from gabru.flask.model import WidgetUIModel


class FakeUser:
    def __init__(self, user_id=1, username="tester", display_name="Tester", is_admin=False, api_key="abcde"):
        self.id = user_id
        self.username = username
        self.display_name = display_name
        self.is_admin = is_admin
        self.api_key = api_key


class FakeAuthUserService:
    def __init__(self, user=None):
        self.user = user or FakeUser()
        self.calls = 0

    def authenticate_api_key(self, api_key):
        self.calls += 1
        if api_key == self.user.api_key:
            return self.user
        return None


class DemoModel(WidgetUIModel):
    id: Optional[int] = Field(default=None, edit_enabled=False)
    name: str = Field(default="")


class FakeCrudService:
    def __init__(self):
        self.created = []

    def create(self, obj):
        self.created.append(obj)
        return 1

    def get_recent_items(self, limit):
        return []

    def get_by_id(self, entity_id):
        return None

    def update(self, obj):
        return True

    def delete(self, entity_id):
        return True

    def count(self):
        return 0


class FakeApplicationService:
    def get_by_name(self, name):
        return None

    def set_active_status(self, name, active):
        return True


class FakeSignupUserService:
    def __init__(self):
        self.created_users = []

    def authenticate(self, username, password):
        return None

    def get_by_username(self, username):
        return None

    def count(self):
        return 0

    def create(self, user):
        self.created_users.append(user)
        return 123


class PermissionManagerTests(unittest.TestCase):
    def setUp(self):
        PermissionManager._user_service = None

    def tearDown(self):
        PermissionManager._user_service = None

    def test_api_key_auth_is_cached_per_request(self):
        app = Flask(__name__)
        app.secret_key = "test-secret"
        fake_service = FakeAuthUserService(FakeUser(user_id=7, api_key="qDdyg"))
        PermissionManager._user_service = fake_service

        with app.test_request_context("/", headers={"X-API-Key": "qDdyg"}):
            self.assertTrue(PermissionManager.is_authenticated())
            self.assertEqual(PermissionManager.get_current_user_id(), 7)
            self.assertEqual(PermissionManager.get_current_user()["auth_type"], "api_key")
            self.assertTrue(PermissionManager.is_authenticated())
            self.assertEqual(fake_service.calls, 1)

    def test_session_auth_takes_precedence(self):
        app = Flask(__name__)
        app.secret_key = "test-secret"
        fake_service = FakeAuthUserService(FakeUser(user_id=9, api_key="qDdyg"))
        PermissionManager._user_service = fake_service

        with app.test_request_context("/", headers={"X-API-Key": "qDdyg"}):
            from flask import session
            session["user_id"] = 3
            session["username"] = "session-user"
            session["display_name"] = "Session User"
            session["is_admin"] = True
            self.assertTrue(PermissionManager.is_authenticated())
            self.assertEqual(PermissionManager.get_current_user_id(), 3)
            self.assertEqual(PermissionManager.get_current_user()["auth_type"], "session")
            self.assertEqual(fake_service.calls, 0)


class AppRequestParsingTests(unittest.TestCase):
    def _build_client(self):
        flask_app = Flask(__name__)
        flask_app.secret_key = "test-secret"
        demo_app = App("Demo", service=FakeCrudService(), model_class=DemoModel)
        flask_app.register_blueprint(demo_app.blueprint, url_prefix="/demo")
        return flask_app.test_client()

    def test_create_rejects_non_object_json(self):
        client = self._build_client()
        with mock.patch.object(PermissionManager, "is_authenticated", return_value=True), \
             mock.patch.object(PermissionManager, "can_write", return_value=True), \
             mock.patch.object(PermissionManager, "can_access_route", return_value=True):
            response = client.post("/demo/", data="[]", content_type="application/json")
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.get_json()["error"], "JSON request body is required")

    def test_create_accepts_object_json(self):
        client = self._build_client()
        with mock.patch.object(PermissionManager, "is_authenticated", return_value=True), \
             mock.patch.object(PermissionManager, "can_write", return_value=True), \
             mock.patch.object(PermissionManager, "can_access_route", return_value=True):
            response = client.post("/demo/", json={"name": "clean"})
        self.assertEqual(response.status_code, 200)


class SignupFlowTests(unittest.TestCase):
    def test_first_signup_sets_session_user_id(self):
        fake_user_service = FakeSignupUserService()
        with mock.patch("gabru.flask.server.ApplicationService", return_value=FakeApplicationService()), \
             mock.patch("gabru.flask.server.UserService", return_value=fake_user_service):
            server = Server("TestServer")
            client = server.app.test_client()
            response = client.post("/signup", json={"username": "admin", "password": "secret"})

            self.assertEqual(response.status_code, 201)
            with client.session_transaction() as session:
                self.assertEqual(session["user_id"], 123)
                self.assertEqual(session["username"], "admin")


if __name__ == "__main__":
    unittest.main()
