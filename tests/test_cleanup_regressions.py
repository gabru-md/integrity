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
from gabru.flask.util import render_flask_template

BASE_DIR = os.path.dirname(os.path.dirname(__file__))


class FakeUser:
    def __init__(
        self,
        user_id=1,
        username="tester",
        display_name="Tester",
        is_admin=False,
        api_key="abcde",
        onboarding_completed=False,
        experience_mode="everyday",
    ):
        self.id = user_id
        self.username = username
        self.display_name = display_name
        self.is_admin = is_admin
        self.api_key = api_key
        self.onboarding_completed = onboarding_completed
        self.experience_mode = experience_mode


class FakeAuthProvider:
    def __init__(self, user=None):
        base_user = user or FakeUser()
        self.user = AuthenticatedUser(
            id=base_user.id,
            username=base_user.username,
            display_name=base_user.display_name,
            is_admin=base_user.is_admin,
            api_key=base_user.api_key,
            experience_mode=base_user.experience_mode,
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


class RegistryDemoModel(WidgetUIModel):
    id: Optional[int] = Field(default=None, edit_enabled=False)
    title: str = Field(default="")


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
    def get_notification_center_data(self):
        return {
            "items": [
                {
                    "id": "in-app:1",
                    "notification_id": 1,
                    "title": "Report ready",
                    "body": "Your report is ready to review.",
                    "href": "/reports/1/view",
                    "class": "review",
                    "created_at": "2026-04-02T12:00:00+00:00",
                    "created_at_display": "Apr 02, 12:00",
                    "is_system": False,
                }
            ],
            "unread_count": 1,
            "has_items": True,
        }

    def mark_notification_read(self, notification_id: int):
        return notification_id == 1

    def mark_all_notifications_read(self):
        return True

    def get_capture_data(self):
        return {
            "recent_activities": [
                {
                    "id": 9,
                    "name": "Quick note walk",
                    "event_type": "walk:logged",
                    "description": "Log a walk quickly.",
                    "tags": ["health", "outdoors"],
                }
            ],
            "suggested_event_types": ["travel:arrival", "meeting:logged"],
            "suggested_tags": ["travel", "important"],
            "latest_event": {"event_type": "travel:arrival", "description": "Arrived safely", "timestamp": "2026-04-02T12:00:00+00:00"},
        }

    def get_dependency_health_data(self):
        return []

    def get_reliability_data(self, processes_data):
        return []

    def get_admin_health_data(self, processes_data):
        return {
            "checked_at": "2026-04-02T12:00:00+00:00",
            "checked_at_display": "2026-04-02 12:00 UTC",
            "host": "rasbhari-pi",
            "server": {"status": "Healthy", "summary": "Admin surface reachable now", "detail": "Server is responding."},
            "event_flow": {"status": "Healthy", "summary": "Last event 3m ago", "detail": "Latest event id: 42"},
            "queue_drift": {"status": "Healthy", "summary": "Max lag 2 events", "detail": "1 queue processor tracked.", "processors": []},
            "dependencies": {"status": "Healthy", "summary": "0 issue(s) detected", "detail": "All checks healthy."},
            "reliability_cards": [],
        }

    def get_universal_timeline_data(self, limit=20):
        return []


class FakeAdminOpsProvider:
    def get_update_status(self):
        return {
            "configured": True,
            "configuration_error": None,
            "repo_dir": "~/Desktop/apps/integrity",
            "service_name": "rasbhari",
            "script_path": "~/Desktop/apps/integrity/scripts/update_rasbhari_host.sh",
            "branch_name": "main",
            "remote_name": "origin",
            "healthcheck_url": "http://127.0.0.1:5000/login",
            "current_commit": "abc123def456",
            "latest_remote_commit": "fed456abc123",
            "update_available": True,
            "dirty_worktree": False,
            "state": "idle",
            "message": "Update is available.",
            "started_at": None,
            "finished_at": None,
            "actor_username": None,
            "output_lines": ["Current commit: abc123def456", "Target commit: fed456abc123"],
            "last_result": "success",
        }

    def trigger_update(self, actor_username=None):
        return {"started": True, "status": self.get_update_status()}


class FakeQueueStats:
    def __init__(self, last_consumed_id=0):
        self.last_consumed_id = last_consumed_id


class FakeQueueProcessor:
    def __init__(self, enabled=False, last_consumed_id=0):
        self.enabled = enabled
        self.q_stats = FakeQueueStats(last_consumed_id=last_consumed_id)
        self.queue = [1, 2, 3]
        self.reloaded_to = None
        self.service = mock.Mock()
        self.service.get_recent_items.return_value = [mock.Mock(id=99)]

    def reload_queue_state(self, last_consumed_id):
        self.reloaded_to = last_consumed_id
        self.q_stats.last_consumed_id = last_consumed_id
        self.queue = []


class FakeProcessManager:
    def __init__(self):
        self.all_processes_map = {"PromiseProcessor": FakeQueueProcessor(enabled=True, last_consumed_id=7)}

    def get_process_status(self, name):
        return False

    def enable_process(self, name):
        return True

    def disable_process(self, name):
        return True

    def run_process(self, name):
        return True

    def pause_process(self, name):
        return True


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
            session["onboarding_completed"] = False
            self.assertTrue(PermissionManager.is_authenticated())
            self.assertEqual(PermissionManager.get_current_user_id(), 3)
            self.assertEqual(PermissionManager.get_current_user()["auth_type"], "session")
            self.assertFalse(PermissionManager.get_current_user()["onboarding_completed"])
            self.assertEqual(fake_service.calls, 0)

    def test_login_stores_onboarding_state_in_session(self):
        app = Flask(__name__)
        app.secret_key = "test-secret"

        with app.test_request_context("/"):
            PermissionManager.login(FakeUser(user_id=4, onboarding_completed=True))
            self.assertTrue(PermissionManager.get_current_user()["onboarding_completed"])


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


class MentalModelContextTests(unittest.TestCase):
    def test_render_template_injects_mental_model(self):
        app = Flask(__name__, template_folder=os.path.join(BASE_DIR, "templates"))
        app.secret_key = "test-secret"

        with app.test_request_context("/"):
            rendered = render_flask_template(
                "home.html",
                widgets_data=[],
                reliability_data=[],
                universal_timeline=[],
                PermissionManager=mock.Mock(can_view_app=lambda *_: False),
                active_app_names=set(),
                current_user={"id": 1, "username": "tester", "display_name": "Tester", "is_admin": False, "onboarding_completed": False},
                Role=mock.Mock(),
            )

        self.assertIn("Rasbhari Apps Dashboard", rendered)
        self.assertNotIn("How Rasbhari Works", rendered)
        self.assertIn("Operations", rendered)

    def test_app_instructions_render_helper_sections(self):
        app = Flask(__name__, template_folder=os.path.join(BASE_DIR, "templates"))
        app.secret_key = "test-secret"

        with app.test_request_context("/events/home"):
            rendered = render_flask_template(
                "_app_instructions.html",
                app_name="Events",
                user_guidance={
                    "overview": "Overview",
                    "app_purpose": "Purpose copy",
                    "how_to_use": ["Use it well"],
                    "setup_leverage": ["Make setup count"],
                    "pairs_with": ["Promises", "Skills"],
                    "ecosystem_fit": {"headline": "How this app fits Rasbhari", "summary": "Connected", "stages": ["Capture"]},
                    "glossary": [],
                    "fields": [],
                    "examples": [],
                },
            )

        self.assertIn("How to use it", rendered)
        self.assertIn("Make setup count", rendered)
        self.assertIn("Pairs with", rendered)


class DashboardRouteTests(unittest.TestCase):
    def test_home_uses_dashboard_template_and_dashboard_route_still_exists(self):
        fake_auth_provider = FakeAuthProvider()
        server = Server(
            "TestServer",
            template_folder=os.path.join(BASE_DIR, "templates"),
            static_folder=os.path.join(BASE_DIR, "static"),
            auth_provider=fake_auth_provider,
            app_status_store=FakeAppStatusStore(),
            dashboard_provider=FakeDashboardProvider(),
            admin_ops_provider=FakeAdminOpsProvider(),
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
        self.assertIn(b"Rasbhari Apps Dashboard", home_response.data)
        self.assertEqual(dashboard_response.status_code, 200)
        self.assertIn(b"Rasbhari Apps Dashboard", dashboard_response.data)

    def test_capture_route_renders_remote_logging_surface(self):
        fake_auth_provider = FakeAuthProvider()
        server = Server(
            "TestServer",
            template_folder=os.path.join(BASE_DIR, "templates"),
            static_folder=os.path.join(BASE_DIR, "static"),
            auth_provider=fake_auth_provider,
            app_status_store=FakeAppStatusStore(),
            dashboard_provider=FakeDashboardProvider(),
            admin_ops_provider=FakeAdminOpsProvider(),
        )
        client = server.app.test_client()

        with client.session_transaction() as session:
            session["user_id"] = 1
            session["username"] = "tester"
            session["display_name"] = "Tester"
            session["is_admin"] = False

        response = client.get("/capture")

        self.assertEqual(response.status_code, 200)
        self.assertIn(b"Remote Capture", response.data)
        self.assertIn(b"Log it before it disappears", response.data)
        self.assertIn(b"Recent Activities", response.data)
        self.assertIn(b"Quick Log", response.data)

    def test_appearance_route_renders_first_class_preferences_surface(self):
        fake_auth_provider = FakeAuthProvider()
        server = Server(
            "TestServer",
            template_folder=os.path.join(BASE_DIR, "templates"),
            static_folder=os.path.join(BASE_DIR, "static"),
            auth_provider=fake_auth_provider,
            app_status_store=FakeAppStatusStore(),
            dashboard_provider=FakeDashboardProvider(),
            admin_ops_provider=FakeAdminOpsProvider(),
        )
        client = server.app.test_client()

        with client.session_transaction() as session:
            session["user_id"] = 1
            session["username"] = "tester"
            session["display_name"] = "Tester"
            session["is_admin"] = False

        response = client.get("/appearance")

        self.assertEqual(response.status_code, 200)
        self.assertIn(b"Tune how Rasbhari feels", response.data)
        self.assertIn(b"Color Direction", response.data)
        self.assertIn(b"Information Weight", response.data)

    def test_admin_overview_requires_system_mode_admin_and_renders_for_system_admin(self):
        fake_auth_provider = FakeAuthProvider()
        server = Server(
            "TestServer",
            template_folder=os.path.join(BASE_DIR, "templates"),
            static_folder=os.path.join(BASE_DIR, "static"),
            auth_provider=fake_auth_provider,
            app_status_store=FakeAppStatusStore(),
            dashboard_provider=FakeDashboardProvider(),
            admin_ops_provider=FakeAdminOpsProvider(),
        )
        client = server.app.test_client()

        with client.session_transaction() as session:
            session["user_id"] = 1
            session["username"] = "tester"
            session["display_name"] = "Tester"
            session["is_admin"] = False
            session["experience_mode"] = "everyday"

        non_admin_response = client.get("/admin")
        self.assertEqual(non_admin_response.status_code, 403)

        with client.session_transaction() as session:
            session["is_admin"] = True
            session["experience_mode"] = "structured"

        structured_admin_response = client.get("/admin")
        self.assertEqual(structured_admin_response.status_code, 403)

        with client.session_transaction() as session:
            session["experience_mode"] = "system"

        admin_response = client.get("/admin")
        self.assertEqual(admin_response.status_code, 200)
        self.assertIn(b"Admin Control Plane", admin_response.data)
        self.assertIn(b"Admin Control Plane", admin_response.data)
        self.assertIn(b"Pi Health Snapshot", admin_response.data)
        self.assertIn(b"Server Availability", admin_response.data)
        self.assertIn(b"Queue Drift", admin_response.data)
        self.assertIn(b"Primary Control", admin_response.data)
        self.assertIn(b"Code Update and Approvals", admin_response.data)
        self.assertIn(b"Code Update", admin_response.data)
        self.assertIn(b"Update To Latest", admin_response.data)

    def test_admin_update_routes_require_system_mode_admin_and_return_status(self):
        fake_auth_provider = FakeAuthProvider()
        server = Server(
            "TestServer",
            template_folder=os.path.join(BASE_DIR, "templates"),
            static_folder=os.path.join(BASE_DIR, "static"),
            auth_provider=fake_auth_provider,
            app_status_store=FakeAppStatusStore(),
            dashboard_provider=FakeDashboardProvider(),
            admin_ops_provider=FakeAdminOpsProvider(),
        )
        client = server.app.test_client()

        with client.session_transaction() as session:
            session["user_id"] = 1
            session["username"] = "tester"
            session["display_name"] = "Tester"
            session["is_admin"] = False
            session["experience_mode"] = "everyday"

        self.assertEqual(client.get("/admin/update/status").status_code, 403)
        self.assertEqual(client.post("/admin/update").status_code, 403)

        with client.session_transaction() as session:
            session["is_admin"] = True
            session["experience_mode"] = "structured"

        self.assertEqual(client.get("/admin/update/status").status_code, 403)
        self.assertEqual(client.post("/admin/update").status_code, 403)

        with client.session_transaction() as session:
            session["experience_mode"] = "system"

        status_response = client.get("/admin/update/status")
        trigger_response = client.post("/admin/update")

        self.assertEqual(status_response.status_code, 200)
        self.assertEqual(status_response.get_json()["current_commit"], "abc123def456")
        self.assertEqual(trigger_response.status_code, 202)
        self.assertTrue(trigger_response.get_json()["started"])

    def test_app_registry_renders_operator_framing_and_app_metadata(self):
        fake_auth_provider = FakeAuthProvider()
        server = Server(
            "TestServer",
            template_folder=os.path.join(BASE_DIR, "templates"),
            static_folder=os.path.join(BASE_DIR, "static"),
            auth_provider=fake_auth_provider,
            app_status_store=FakeAppStatusStore(),
            dashboard_provider=FakeDashboardProvider(),
        )
        demo_app = App(
            "DemoRegistry",
            service=FakeCrudService(),
            model_class=RegistryDemoModel,
            user_guidance={
                "app_purpose": "Use this app to structure demo records for the ecosystem.",
                "setup_leverage": ["Enable the widget only if the data is worth surfacing."],
                "pairs_with": ["Projects", "Dashboard"],
                "ecosystem_fit": {
                    "headline": "How this app fits Rasbhari",
                    "summary": "It supports the structure layer and feeds later views.",
                    "stages": ["Structure", "Reflect"],
                },
            },
        )
        demo_app.register_process(FakeQueueProcessor, enabled=True)
        server.register_app(demo_app)
        server.process_manager = FakeProcessManager()
        client = server.app.test_client()

        with client.session_transaction() as session:
            session["user_id"] = 1
            session["username"] = "tester"
            session["display_name"] = "Tester"
            session["is_admin"] = True
            session["experience_mode"] = "system"

        response = client.get("/apps")

        self.assertEqual(response.status_code, 200)
        self.assertIn(b"Registered Applications", response.data)
        self.assertIn(b"Ownership", response.data)
        self.assertIn(b"Process-Backed", response.data)
        self.assertIn(b"Works With", response.data)
        self.assertIn(b"Demoregistry", response.data)


class ProcessAdminRouteTests(unittest.TestCase):
    def test_admin_can_update_queue_processor_progress(self):
        fake_auth_provider = FakeAuthProvider(FakeUser(is_admin=True, experience_mode="system"))
        server = Server(
            "TestServer",
            template_folder=os.path.join(BASE_DIR, "templates"),
            static_folder=os.path.join(BASE_DIR, "static"),
            auth_provider=fake_auth_provider,
            app_status_store=FakeAppStatusStore(),
            dashboard_provider=FakeDashboardProvider(),
        )
        server.process_manager = FakeProcessManager()
        client = server.app.test_client()

        with client.session_transaction() as session:
            session["user_id"] = 1
            session["username"] = "tester"
            session["display_name"] = "Tester"
            session["is_admin"] = True
            session["experience_mode"] = "system"

        with mock.patch("gabru.flask.server.QueueService") as queue_service_cls:
            queue_service = queue_service_cls.return_value
            queue_service.set_last_consumed_id.return_value = mock.Mock(last_consumed_id=42)

            response = client.post("/process_progress/PromiseProcessor", json={"last_consumed_id": 42})

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.get_json()["last_consumed_id"], 42)
        queue_service.set_last_consumed_id.assert_called_once_with("PromiseProcessor", 42)
        self.assertEqual(server.process_manager.all_processes_map["PromiseProcessor"].q_stats.last_consumed_id, 42)
        self.assertEqual(server.process_manager.all_processes_map["PromiseProcessor"].reloaded_to, 42)
        self.assertEqual(server.process_manager.all_processes_map["PromiseProcessor"].queue, [])

    def test_process_progress_rejects_non_admin(self):
        fake_auth_provider = FakeAuthProvider(FakeUser(is_admin=False, experience_mode="everyday"))
        server = Server(
            "TestServer",
            template_folder=os.path.join(BASE_DIR, "templates"),
            static_folder=os.path.join(BASE_DIR, "static"),
            auth_provider=fake_auth_provider,
            app_status_store=FakeAppStatusStore(),
            dashboard_provider=FakeDashboardProvider(),
        )
        server.process_manager = FakeProcessManager()
        client = server.app.test_client()

        with client.session_transaction() as session:
            session["user_id"] = 1
            session["username"] = "tester"
            session["display_name"] = "Tester"
            session["is_admin"] = False
            session["experience_mode"] = "everyday"

        response = client.post("/process_progress/PromiseProcessor", json={"last_consumed_id": 42})

        self.assertEqual(response.status_code, 403)

    def test_admin_can_jump_queue_processor_to_latest(self):
        fake_auth_provider = FakeAuthProvider(FakeUser(is_admin=True, experience_mode="system"))
        server = Server(
            "TestServer",
            template_folder=os.path.join(BASE_DIR, "templates"),
            static_folder=os.path.join(BASE_DIR, "static"),
            auth_provider=fake_auth_provider,
            app_status_store=FakeAppStatusStore(),
            dashboard_provider=FakeDashboardProvider(),
        )
        server.process_manager = FakeProcessManager()
        client = server.app.test_client()

        with client.session_transaction() as session:
            session["user_id"] = 1
            session["username"] = "tester"
            session["display_name"] = "Tester"
            session["is_admin"] = True
            session["experience_mode"] = "system"

        with mock.patch("gabru.flask.server.QueueService") as queue_service_cls:
            queue_service = queue_service_cls.return_value
            queue_service.set_last_consumed_id.return_value = mock.Mock(last_consumed_id=99)

            response = client.post("/process_progress/PromiseProcessor/latest")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.get_json()["last_consumed_id"], 99)
        queue_service.set_last_consumed_id.assert_called_once_with("PromiseProcessor", 99)
        self.assertEqual(server.process_manager.all_processes_map["PromiseProcessor"].reloaded_to, 99)

    def test_admin_can_restart_process(self):
        fake_auth_provider = FakeAuthProvider(FakeUser(is_admin=True, experience_mode="system"))
        server = Server(
            "TestServer",
            template_folder=os.path.join(BASE_DIR, "templates"),
            static_folder=os.path.join(BASE_DIR, "static"),
            auth_provider=fake_auth_provider,
            app_status_store=FakeAppStatusStore(),
            dashboard_provider=FakeDashboardProvider(),
        )
        process_manager = FakeProcessManager()
        process_manager.pause_process = mock.Mock(return_value=True)
        process_manager.run_process = mock.Mock(return_value=True)
        server.process_manager = process_manager
        client = server.app.test_client()

        with client.session_transaction() as session:
            session["user_id"] = 1
            session["username"] = "tester"
            session["display_name"] = "Tester"
            session["is_admin"] = True
            session["experience_mode"] = "system"

        response = client.post("/restart_process/PromiseProcessor")

        self.assertEqual(response.status_code, 200)
        process_manager.pause_process.assert_called_once_with("PromiseProcessor")
        process_manager.run_process.assert_called_once_with("PromiseProcessor")


class NotificationShellTests(unittest.TestCase):
    def test_home_renders_notification_trigger_and_notice(self):
        fake_auth_provider = FakeAuthProvider(FakeUser(is_admin=False, experience_mode="everyday"))
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
            session["experience_mode"] = "everyday"

        response = client.get("/")

        self.assertEqual(response.status_code, 200)
        self.assertIn(b"Notifications", response.data)
        self.assertIn(b"Report ready", response.data)

    def test_mark_notification_read_route_uses_dashboard_provider(self):
        fake_auth_provider = FakeAuthProvider(FakeUser(is_admin=False, experience_mode="everyday"))
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
            session["experience_mode"] = "everyday"

        response = client.post("/notifications/1/read")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.get_json()["unread_count"], 1)


if __name__ == "__main__":
    unittest.main()
