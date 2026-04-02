from __future__ import annotations

import os
import threading
from datetime import datetime, timezone
from typing import Optional

from flask import Flask, redirect, send_from_directory, jsonify, request
from gabru.log import Logger
from gabru.contracts import AppStatusStore, AssistantCommandProvider, AuthProvider, DashboardDataProvider
from gabru.flask.app import App
from gabru.auth import PermissionManager, Role, admin_required, login_required

from gabru.process import ProcessManager
from gabru.qprocessor.qprocessor import QueueProcessor
from gabru.flask.util import render_flask_template

from dotenv import load_dotenv

load_dotenv()

SERVER_FILES_FOLDER = os.getenv("SERVER_FILES_FOLDER", "/tmp")


class Server:
    def __init__(
        self,
        name: str,
        template_folder="templates",
        static_folder="static",
        auth_provider: Optional[AuthProvider] = None,
        app_status_store: Optional[AppStatusStore] = None,
        dashboard_provider: Optional[DashboardDataProvider] = None,
        assistant_provider: Optional[AssistantCommandProvider] = None,
    ):
        self.name = name
        self.app = Flask(__name__, template_folder=template_folder, static_folder=static_folder)
        self.app.secret_key = os.getenv("FLASK_SECRET_KEY", "super-secret-key-for-sessions")
        self.setup_default_routes()
        self.setup_auth_context()
        self.not_allowed_app_names = []
        self.log = Logger.get_log(self.name)
        self.registered_apps = []
        self.auth_provider = auth_provider
        self.app_status_store = app_status_store
        self.dashboard_provider = dashboard_provider
        self.assistant_provider = assistant_provider
        if self.auth_provider:
            PermissionManager.configure(self.auth_provider)
        self.process_manager = None
        self.process_manager_thread = None

    def setup_auth_context(self):
        @self.app.context_processor
        def inject_permissions():
            active_app_names = {
                app.name.lower()
                for app in self.registered_apps
                if getattr(app, "is_active", False)
            }
            return dict(
                PermissionManager=PermissionManager,
                current_role=PermissionManager.get_current_role(),
                current_user=PermissionManager.get_current_user(),
                Role=Role,
                active_app_names=active_app_names,
            )

    def register_app(self, app: App):
        if app.name.lower() in self.not_allowed_app_names:
            raise Exception("Could not register app")

        # Sync application status with the database
        db_state = self.app_status_store.get_app_state(app.name) if self.app_status_store else None
        if db_state is None:
            if self.app_status_store:
                self.app_status_store.set_app_state(app.name, True)
            app.is_active = True
        else:
            app.is_active = db_state

        self.registered_apps.append(app)
        app.server_instance = self # give it the server instance
        self.app.register_blueprint(app.blueprint, url_prefix=f"/{app.name.lower()}")

    def run(self):
        debug_enabled = self._env_flag("SERVER_DEBUG")
        self.app.run(
            debug=debug_enabled,
            use_reloader=debug_enabled,
            host='0.0.0.0',
            port=int(os.getenv("SERVER_PORT", 5000))
        )

    def setup_default_routes(self):
        @self.app.route('/')
        @login_required
        def home():
            today_data = self.get_today_data()
            return render_flask_template('today.html', today_data=today_data)

        @self.app.route('/dashboard')
        @login_required
        def dashboard():
            widgets_data = self.get_widgets_data()
            reliability_data = self.get_reliability_data() if PermissionManager.is_admin() else []
            universal_timeline = self.get_universal_timeline_data() if PermissionManager.is_admin() else []
            return render_flask_template(
                'home.html',
                widgets_data=widgets_data,
                reliability_data=reliability_data,
                universal_timeline=universal_timeline
            )

        @self.app.route('/login', methods=['GET', 'POST'])
        def login():
            if request.method == 'GET':
                if PermissionManager.is_authenticated():
                    return redirect('/')
                return render_flask_template('login.html', next_url=request.args.get('next', '/'))

            data = request.json if request.is_json else request.form
            username = (data.get('username') or '').strip().lower()
            password = data.get('password') or ''
            next_url = data.get('next') or '/'

            if self.auth_provider is None:
                raise RuntimeError("Server auth provider is not configured")

            user = self.auth_provider.authenticate_credentials(username, password)
            if not user:
                # check if user exists but not approved
                existing_user = self.auth_provider.get_by_username(username)
                error_msg = "Invalid username or password"
                if existing_user and not existing_user.is_approved:
                    error_msg = "Your account is pending admin approval."
                elif existing_user and not existing_user.is_active:
                    error_msg = "Your account has been deactivated."
                
                if request.is_json:
                    return jsonify({"error": error_msg}), 401
                return render_flask_template('login.html', next_url=next_url, error=error_msg), 401

            PermissionManager.login(user)
            if request.is_json:
                return jsonify({"message": "Login successful", "redirect": next_url or "/"})
            return redirect(next_url or '/')

        @self.app.route('/signup', methods=['GET', 'POST'])
        def signup():
            if request.method == 'GET':
                if PermissionManager.is_authenticated():
                    return redirect('/')
                return render_flask_template('signup.html')

            data = request.json if request.is_json else request.form
            username = (data.get('username') or '').strip().lower()
            display_name = (data.get('display_name') or '').strip()
            password = data.get('password') or ''

            if not username or not password:
                error = "Username and password are required."
                if request.is_json: return jsonify({"error": error}), 400
                return render_flask_template('signup.html', error=error), 400

            if self.auth_provider is None:
                raise RuntimeError("Server auth provider is not configured")

            if self.auth_provider.get_by_username(username):
                error = "Username already exists."
                if request.is_json: return jsonify({"error": error}), 400
                return render_flask_template('signup.html', error=error), 400

            # The first user in the system is automatically an admin and approved
            is_first_user = self.auth_provider.count_users() == 0

            created_user = self.auth_provider.create_user(
                username=username,
                display_name=display_name or username,
                password=password,
                is_admin=is_first_user,
                is_active=True,
                is_approved=is_first_user,
            )
            if created_user:
                if is_first_user:
                    # Log them in immediately if they are the first user/admin
                    PermissionManager.login(created_user)
                    if request.is_json:
                        return jsonify({"message": "Admin account created successfully", "redirect": "/"}), 201
                    return redirect('/')
                
                if request.is_json:
                    return jsonify({"message": "Signup successful, pending approval", "redirect": "/login"}), 201
                return render_flask_template('signup.html', success=True)
            
            error = "Failed to create account. Please try again."
            if request.is_json: return jsonify({"error": error}), 500
            return render_flask_template('signup.html', error=error), 500

        @self.app.route('/logout', methods=['POST'])
        @login_required
        def logout():
            PermissionManager.logout()
            if request.is_json:
                return jsonify({"message": "Logged out"}), 200
            return redirect('/login')

        @self.app.route('/apps')
        @admin_required
        def apps():
            apps_data = self.get_apps_data()
            return render_flask_template('apps.html', apps_data=apps_data)

        @self.app.route('/processes')
        @admin_required
        def processes():
            processes_data = self.get_processes_data()
            dependency_health_data = self.get_dependency_health_data()
            return render_flask_template('processes.html', processes_data=processes_data, dependency_health_data=dependency_health_data)
        
        @self.app.route('/heimdall')
        @admin_required
        def heimdall():
            return render_flask_template('heimdall.html')

        @self.app.route('/devices')
        @admin_required
        def devices():
            return redirect('/devices/home')

        @self.app.route('/assistant/command', methods=['POST'])
        @login_required
        def assistant_command():
            data = request.get_json(silent=True)
            if not isinstance(data, dict):
                return jsonify({"error": "JSON request body is required"}), 400

            message = (data.get("message") or "").strip()
            cancel = bool(data.get("cancel"))
            change_action = (data.get("change_action") or "").strip() or None
            if not message and not cancel and not change_action:
                return jsonify({"error": "message is required"}), 400

            user_id = PermissionManager.get_current_user_id()
            if user_id is None:
                return jsonify({"error": "Unable to determine current user"}), 401
            if self.assistant_provider is None:
                return jsonify({"error": "Assistant provider is not configured"}), 500

            confirm = bool(data.get("confirm"))
            result = self.assistant_provider.handle(
                user_id=user_id,
                message=message,
                confirm=confirm,
                cancel=cancel,
                change_action=change_action,
            )
            status_code = 200 if result.ok else 500
            return jsonify(result.model_dump()), status_code

        @self.app.route('/assistant/recommendation', methods=['POST'])
        @login_required
        def assistant_recommendation():
            data = request.get_json(silent=True)
            if not isinstance(data, dict):
                return jsonify({"error": "JSON request body is required"}), 400

            recommendation = data.get("recommendation")
            if not isinstance(recommendation, dict):
                return jsonify({"error": "recommendation object is required"}), 400

            user_id = PermissionManager.get_current_user_id()
            if user_id is None:
                return jsonify({"error": "Unable to determine current user"}), 401
            if self.assistant_provider is None:
                return jsonify({"error": "Assistant provider is not configured"}), 500

            result = self.assistant_provider.handle_recommendation(user_id=user_id, recommendation=recommendation)
            status_code = 200 if result.ok else 500
            return jsonify(result.model_dump()), status_code

        @self.app.route('/download/<filename>')
        @login_required
        def download(filename):
            return send_from_directory(directory=SERVER_FILES_FOLDER, path=filename, as_attachment=True)

        @self.app.route('/enable_app/<app_name>', methods=['POST'])
        @admin_required
        def enable_app(app_name):
            for app in self.registered_apps:
                if app.name.lower() == app_name.lower():
                    app.is_active = True
                    if self.app_status_store:
                        self.app_status_store.set_app_state(app.name, True)
                    return jsonify({"message": f"App {app.name} enabled successfully"}), 200
            return jsonify({"error": f"App {app_name} not found"}), 404

        @self.app.route('/disable_app/<app_name>', methods=['POST'])
        @admin_required
        def disable_app(app_name):
            for app in self.registered_apps:
                if app.name.lower() == app_name.lower():
                    app.is_active = False
                    if self.app_status_store:
                        self.app_status_store.set_app_state(app.name, False)
                    return jsonify({"message": f"App {app.name} disabled successfully"}), 200
            return jsonify({"error": f"App {app_name} not found"}), 404

        @self.app.route('/enable_process/<process_name>', methods=['POST'])
        @admin_required
        def enable_process(process_name):
            if self.process_manager:
                success = self.process_manager.enable_process(process_name)
                if success:
                    return jsonify({"message": f"Process {process_name} enabled successfully"}), 200
                else:
                    return jsonify({"error": f"Failed to enable process {process_name}"}), 500
            return jsonify({"error": "Process Manager is not initialized"}), 500

        @self.app.route('/disable_process/<process_name>', methods=['POST'])
        @admin_required
        def disable_process(process_name):
            if self.process_manager:
                success = self.process_manager.disable_process(process_name)
                if success:
                    return jsonify({"message": f"Process {process_name} disabled successfully"}), 200
                else:
                    return jsonify({"error": f"Failed to disable process {process_name}"}), 500
            return jsonify({"error": "Process Manager is not initialized"}), 500
        
        @self.app.route('/start_process/<process_name>', methods=['POST'])
        @admin_required
        def start_process(process_name):
            if self.process_manager:
                success = self.process_manager.run_process(process_name)
                if success:
                    return jsonify({"message": f"Process {process_name} started successfully"}), 200
                else:
                    return jsonify({"error": f"Failed to start process {process_name}"}), 500
            return jsonify({"error": "Process Manager is not initialized"}), 500

        @self.app.route('/stop_process/<process_name>', methods=['POST'])
        @admin_required
        def stop_process(process_name):
            if self.process_manager:
                self.process_manager.pause_process(process_name)
                return jsonify({"message": f"Process {process_name} stopped successfully"}), 200
            return jsonify({"error": "Process Manager is not initialized"}), 500

        @self.app.route('/process_logs/<process_name>')
        @admin_required
        def get_process_logs(process_name):
            log_dir = os.getenv('LOG_DIR')
            if not log_dir:
                return jsonify({"error": "LOG_DIR not set"}), 500
            log_file = os.path.join(log_dir, f"{process_name}.log")
            if not os.path.exists(log_file):
                return jsonify({"logs": []}), 404
            with open(log_file, 'r') as f:
                lines = f.readlines()
                return jsonify({"logs": lines[-100:]})

    def get_processes_data(self) -> list:
        processes_data = []
        if not self.process_manager: return []
        for app in self.registered_apps:
            for p_class, args, kwargs in app.get_processes():
                name = kwargs.get('name', p_class.__name__)
                instance = self.process_manager.all_processes_map.get(name)
                is_alive = self.process_manager.get_process_status(name) if instance else False
                is_enabled = instance.enabled if instance else kwargs.get('enabled', False)
                
                p_data = { 'name': name, 'is_alive': is_alive, 'is_enabled': is_enabled, 'owner_app': app.name }
                if issubclass(p_class, QueueProcessor) and instance:
                    p_data.update({'type': 'QueueProcessor', 'last_consumed_id': getattr(instance.q_stats, 'last_consumed_id', None)})
                else:
                    p_data.update({'type': 'Process', 'last_consumed_id': None})
                processes_data.append(p_data)
        return processes_data

    def get_dependency_health_data(self) -> list[dict]:
        if not self.dashboard_provider:
            return []
        return self.dashboard_provider.get_dependency_health_data()

    def get_apps_data(self) -> []:
        apps_data = []
        for app in self.registered_apps:
            app_data = {
                'name': app.name,
                'model_class': app.model_class.__name__,
                'processes': [p[0].__name__ for p in app.processes],
                'widget_enabled': app.widget_enabled,
                'is_active': app.is_active
            }
            apps_data.append(app_data)
        return apps_data

    def get_widgets_data(self) -> {}:
        widgets_data = {}
        for app in self.registered_apps:
            # Check if the app is active and current role can view it
            if app.is_active and PermissionManager.can_view_app(app.name):
                widget_data, model_attributes = app.widget_data()
                if widget_data is not None:
                    widgets_data[app.name.capitalize()] = {
                        "data": widget_data,
                        "attributes": model_attributes,
                        "type": app.widget_type,
                        "config": app.widget_config
                    }
        return widgets_data

    def get_reliability_data(self) -> list[dict]:
        processes_data = self.get_processes_data()
        if not self.dashboard_provider:
            return []
        return self.dashboard_provider.get_reliability_data(processes_data)

    def get_today_data(self) -> dict:
        if not self.dashboard_provider:
            return {}
        return self.dashboard_provider.get_today_data()

    def get_universal_timeline_data(self, limit: int = 20) -> list[dict]:
        if not self.dashboard_provider:
            return []
        return self.dashboard_provider.get_universal_timeline_data(limit=limit)

    def _normalize_datetime(self, value) -> datetime | None:
        if value is None:
            return None
        if isinstance(value, datetime):
            if value.tzinfo is None or value.tzinfo.utcoffset(value) is None:
                return value.replace(tzinfo=timezone.utc)
            return value.astimezone(timezone.utc)
        if isinstance(value, (int, float)):
            return datetime.fromtimestamp(value, tz=timezone.utc)
        try:
            parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
            if parsed.tzinfo is None or parsed.tzinfo.utcoffset(parsed) is None:
                return parsed.replace(tzinfo=timezone.utc)
            return parsed.astimezone(timezone.utc)
        except Exception:
            return None

    def _format_age(self, value) -> str:
        dt_value = self._normalize_datetime(value)
        if not dt_value:
            return "unknown"

        delta = datetime.now(timezone.utc) - dt_value
        seconds = max(0, int(delta.total_seconds()))
        if seconds < 60:
            return f"{seconds}s ago"
        if seconds < 3600:
            return f"{seconds // 60}m ago"
        if seconds < 86400:
            return f"{seconds // 3600}h ago"
        return f"{seconds // 86400}d ago"

    def _count_recent_log_failures(self, filename: str, line_limit: int = 200) -> int:
        log_dir = os.getenv('LOG_DIR')
        if not log_dir:
            return 0

        log_path = os.path.join(log_dir, filename)
        if not os.path.exists(log_path):
            return 0

        try:
            with open(log_path, 'r') as log_file:
                lines = log_file.readlines()[-line_limit:]
        except Exception:
            return 0

        failure_markers = (
            "returned error",
            "Could not send",
            "Failed to send",
        )
        return sum(1 for line in lines if any(marker in line for marker in failure_markers))

    def process_manager_init(self):
        processes_to_manage = {}
        self.log.info(f"Starting process manager for {self.name}")
        for app in self.registered_apps:
            app_processes = app.get_processes()
            if app_processes:
                processes_to_manage[app.name] = app_processes
        self.log.info("Loaded all processes to manage")
        self.process_manager = ProcessManager(processes_to_manage=processes_to_manage)
        self.process_manager.start()
        self.process_manager.join()
        self.log.info("All processes concluded.")

    def start_process_manager(self):
        if self._env_flag("SERVER_DEBUG") and os.getenv("WERKZEUG_RUN_MAIN") != "true":
            self.log.info("Skipping process manager startup in Werkzeug reloader parent process.")
            return
        self.process_manager_thread = threading.Thread(target=self.process_manager_init, daemon=True)
        self.process_manager_thread.start()

    def _env_flag(self, key: str, default: bool = False) -> bool:
        value = os.getenv(key)
        if value is None:
            return default
        return value.strip().lower() in {"1", "true", "yes", "on"}
