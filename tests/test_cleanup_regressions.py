import os
import unittest
from unittest import mock
from typing import Optional

from flask import Flask
from pydantic import Field

os.environ.setdefault("LOG_DIR", "/tmp/rasbhari-test-logs")
os.environ.setdefault("FLASK_SECRET_KEY", "test-secret")

from gabru.auth import PermissionManager
from gabru.contracts import AuthenticatedUser
from gabru.flask.app import App
from gabru.flask.server import Server
from gabru.flask.model import WidgetUIModel

BASE_DIR = os.path.dirname(os.path.dirname(__file__))


class FakeUser:
    def __init__(self, user_id=1, username="tester", display_name="Tester", is_admin=False, api_key="abcde"):
        self.id = user_id
        self.username = username
        self.display_name = display_name
        self.is_admin = is_admin
        self.api_key = api_key


class FakeAuthProvider:
    def __init__(self, user=None):
        base_user = user or FakeUser()
        self.user = AuthenticatedUser(
            id=base_user.id,
            username=base_user.username,
            display_name=base_user.display_name,
            is_admin=base_user.is_admin,
            api_key=base_user.api_key,
        )
        self.calls = 0

    def authenticate_api_key(self, api_key):
        self.calls += 1
        if api_key == self.user.api_key:
            return self.user
        return None

    def authenticate_credentials(self, username, password):
        return None

    def get_by_username(self, username):
        return None

    def create_user(self, **kwargs):
        return None

    def count_users(self):
        return 0


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


class FakeAppStatusStore:
    def get_app_state(self, name):
        return None

    def set_app_state(self, name, active):
        return True


class FakeDashboardProvider:
    def get_today_data(self):
        return {"guidance": [{"title": "Start with one meaningful move", "body": "Today route is working.", "href": "/projects/home"}]}

    def get_dependency_health_data(self):
        return []

    def get_reliability_data(self, processes_data):
        return []

    def get_universal_timeline_data(self, limit=20):
        return []


class FakeSignupAuthProvider:
    def __init__(self):
        self.created_users = []

    def authenticate_credentials(self, username, password):
        return None

    def get_by_username(self, username):
        return None

    def count_users(self):
        return 0

    def authenticate_api_key(self, api_key):
        return None

    def create_user(self, username, display_name, password, is_admin, is_active, is_approved):
        user = AuthenticatedUser(
            id=123,
            username=username,
            display_name=display_name,
            is_admin=is_admin,
            api_key=None,
        )
        self.created_users.append(user)
        return user


class PermissionManagerTests(unittest.TestCase):
    def setUp(self):
        PermissionManager._auth_provider = None

    def tearDown(self):
        PermissionManager._auth_provider = None

    def test_api_key_auth_is_cached_per_request(self):
        app = Flask(__name__)
        app.secret_key = "test-secret"
        fake_service = FakeAuthProvider(FakeUser(user_id=7, api_key="qDdyg"))
        PermissionManager.configure(fake_service)

        with app.test_request_context("/", headers={"X-API-Key": "qDdyg"}):
            self.assertTrue(PermissionManager.is_authenticated())
            self.assertEqual(PermissionManager.get_current_user_id(), 7)
            self.assertEqual(PermissionManager.get_current_user()["auth_type"], "api_key")
            self.assertTrue(PermissionManager.is_authenticated())
            self.assertEqual(fake_service.calls, 1)

    def test_session_auth_takes_precedence(self):
        app = Flask(__name__)
        app.secret_key = "test-secret"
        fake_service = FakeAuthProvider(FakeUser(user_id=9, api_key="qDdyg"))
        PermissionManager.configure(fake_service)

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
        fake_auth_provider = FakeSignupAuthProvider()
        server = Server(
            "TestServer",
            auth_provider=fake_auth_provider,
            app_status_store=FakeAppStatusStore(),
        )
        client = server.app.test_client()
        response = client.post("/signup", json={"username": "admin", "password": "secret"})

        self.assertEqual(response.status_code, 201)
        with client.session_transaction() as session:
            self.assertEqual(session["user_id"], 123)
            self.assertEqual(session["username"], "admin")


class TodayRouteTests(unittest.TestCase):
    def test_home_uses_today_template_and_dashboard_route_still_exists(self):
        fake_auth_provider = FakeAuthProvider()
        server = Server(
            "TestServer",
            template_folder=os.path.join(BASE_DIR, "templates"),
            static_folder=os.path.join(BASE_DIR, "static"),
            auth_provider=fake_auth_provider,
            app_status_store=FakeAppStatusStore(),
            dashboard_provider=FakeDashboardProvider(),
        )
        client = server.app.test_client()

        with client.session_transaction() as session:
            session["user_id"] = 1
            session["username"] = "tester"
            session["display_name"] = "Tester"
            session["is_admin"] = False

        home_response = client.get("/")
        dashboard_response = client.get("/dashboard")

        self.assertEqual(home_response.status_code, 200)
        self.assertIn(b"Daily Control Surface", home_response.data)
        self.assertEqual(dashboard_response.status_code, 200)
        self.assertIn(b"Rasbhari Apps Dashboard", dashboard_response.data)


if __name__ == "__main__":
    unittest.main()
