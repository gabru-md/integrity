from __future__ import annotations

import os
import threading
from datetime import datetime, timezone

from flask import Flask, redirect, send_from_directory, jsonify, session, request, abort
from gabru.log import Logger
from gabru.flask.app import App
from gabru.auth import PermissionManager, Role, admin_required, login_required

from gabru.process import ProcessManager
from gabru.qprocessor.qprocessor import QueueProcessor
from gabru.flask.util import render_flask_template
from model.user import User
from services.users import UserService
from services.applications import ApplicationService

from dotenv import load_dotenv

load_dotenv()

SERVER_FILES_FOLDER = os.getenv("SERVER_FILES_FOLDER", "/tmp")


class Server:
    def __init__(self, name: str, template_folder="templates", static_folder="static"):
        self.name = name
        self.app = Flask(__name__, template_folder=template_folder, static_folder=static_folder)
        self.app.secret_key = os.getenv("FLASK_SECRET_KEY", "super-secret-key-for-sessions")
        self.setup_default_routes()
        self.setup_auth_context()
        self.not_allowed_app_names = []
        self.log = Logger.get_log(self.name)
        self.registered_apps = []
        self.application_service = ApplicationService()
        self.process_manager = None
        self.process_manager_thread = None

    def setup_auth_context(self):
        @self.app.context_processor
        def inject_permissions():
            return dict(
                PermissionManager=PermissionManager,
                current_role=PermissionManager.get_current_role(),
                current_user=PermissionManager.get_current_user(),
                Role=Role
            )

    def register_app(self, app: App):
        if app.name.lower() in self.not_allowed_app_names:
            raise Exception("Could not register app")

        # Sync application status with the database
        db_app = self.application_service.get_by_name(app.name)
        if db_app:
            app.is_active = db_app.is_active
        else:
            # First time this app is registered, add to database as active
            self.application_service.set_active_status(app.name, True)
            app.is_active = True

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

            user_service = UserService()
            user = user_service.authenticate(username, password)
            if not user:
                # check if user exists but not approved
                existing_user = user_service.get_by_username(username)
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

            user_service = UserService()
            if user_service.get_by_username(username):
                error = "Username already exists."
                if request.is_json: return jsonify({"error": error}), 400
                return render_flask_template('signup.html', error=error), 400

            # The first user in the system is automatically an admin and approved
            is_first_user = user_service.count() == 0
            
            new_user = User(
                username=username,
                display_name=display_name or username,
                password=password,
                is_admin=is_first_user,
                is_active=True,
                is_approved=is_first_user
            )
            
            user_id = user_service.create(new_user)
            if user_id:
                if is_first_user:
                    # Log them in immediately if they are the first user/admin
                    PermissionManager.login(new_user)
                    new_user.id = user_id
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
                    self.application_service.set_active_status(app.name, True)
                    return jsonify({"message": f"App {app.name} enabled successfully"}), 200
            return jsonify({"error": f"App {app_name} not found"}), 404

        @self.app.route('/disable_app/<app_name>', methods=['POST'])
        @admin_required
        def disable_app(app_name):
            for app in self.registered_apps:
                if app.name.lower() == app_name.lower():
                    app.is_active = False
                    self.application_service.set_active_status(app.name, False)
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
        from services.dependency_health import DependencyHealthService

        try:
            return DependencyHealthService().get_checks()
        except Exception as exc:
            return [{
                "name": "Dependency Health",
                "status": "Broken",
                "summary": "Health checks failed",
                "detail": str(exc),
            }]

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
        from gabru.qprocessor.qservice import QueueService
        from services.devices import DeviceService
        from services.events import EventService
        from services.notifications import NotificationService

        processes_data = self.get_processes_data()
        event_service = EventService()
        notification_service = NotificationService()
        device_service = DeviceService()
        queue_service = QueueService()

        latest_event = next(iter(event_service.get_recent_items(1)), None)
        latest_event_id = latest_event.id if latest_event else 0
        latest_event_age = self._format_age(latest_event.timestamp if latest_event else None)

        running_processes = sum(1 for process in processes_data if process.get('is_alive'))
        total_processes = len(processes_data)
        process_status = "Healthy"
        if total_processes == 0:
            process_status = "Paused"
        elif running_processes == 0:
            process_status = "Broken"
        elif running_processes < total_processes:
            process_status = "Delayed"

        queue_stats = queue_service.get_all()
        queue_lags = [max(0, latest_event_id - (stat.last_consumed_id or 0)) for stat in queue_stats]
        max_queue_lag = max(queue_lags) if queue_lags else 0
        queue_status = "Healthy"
        if max_queue_lag > 100:
            queue_status = "Broken"
        elif max_queue_lag > 20:
            queue_status = "Delayed"
        elif not queue_stats:
            queue_status = "Paused"

        recent_notifications = notification_service.get_recent_items(5)
        courier_failures = self._count_recent_log_failures("Courier.log")
        notification_status = "Healthy"
        if courier_failures > 0:
            notification_status = "Delayed"
        if not any(process['name'] == 'Courier' and process['is_alive'] for process in processes_data):
            notification_status = "Broken"

        enabled_devices = device_service.count(filters={"enabled": True})
        device_processes = [process for process in processes_data if process["owner_app"] == "Devices"]
        active_device_processes = sum(1 for process in device_processes if process.get("is_alive"))
        device_status = "Healthy" if enabled_devices > 0 else "Paused"
        if enabled_devices > 0 and active_device_processes == 0:
            device_status = "Delayed"

        return [
            {
                "name": "Process Health",
                "status": process_status,
                "summary": f"{running_processes}/{total_processes} processes running" if total_processes else "No processes registered",
                "detail": "Background workers that power event handling and automation.",
                "href": "/processes",
            },
            {
                "name": "Event Flow",
                "status": "Healthy" if latest_event else "Paused",
                "summary": f"Last event {latest_event_age}" if latest_event else "No events recorded yet",
                "detail": f"Latest event id: {latest_event_id}" if latest_event else "The event stream is currently empty.",
                "href": "/events/home",
            },
            {
                "name": "Queue Health",
                "status": queue_status,
                "summary": f"Max backlog: {max_queue_lag} events",
                "detail": f"Tracking {len(queue_stats)} queue processors against event stream id {latest_event_id}.",
                "href": "/processes",
            },
            {
                "name": "Notifications",
                "status": notification_status,
                "summary": f"{len(recent_notifications)} recent deliveries, {courier_failures} recent failures",
                "detail": "Courier sends ntfy.sh by default and email when the event carries the email tag.",
                "href": "/processes",
            },
            {
                "name": "Devices",
                "status": device_status,
                "summary": f"{enabled_devices} enabled devices, {active_device_processes}/{len(device_processes)} device processes active",
                "detail": "Tracks sensor/device availability and the workers that monitor them.",
                "href": "/devices",
            },
        ]

    def get_universal_timeline_data(self, limit: int = 20) -> list[dict]:
        from services.events import EventService
        from services.notifications import NotificationService
        from services.skill_level_history import SkillLevelHistoryService
        from services.timeline import TimelineService

        event_service = EventService()
        notification_service = NotificationService()
        skill_history_service = SkillLevelHistoryService()
        project_timeline_service = TimelineService()

        items = []

        for item in skill_history_service.get_recent_history(limit=6):
            items.append({
                "source": "Skills",
                "category": "Growth",
                "title": item.summary,
                "subtitle": f"{item.total_xp} XP total",
                "timestamp": item.reached_at,
                "href": "/skills/home",
            })

        for item in project_timeline_service.get_recent_items(6):
            items.append({
                "source": "Projects",
                "category": "Projects",
                "title": item.content[:80] + ("..." if len(item.content) > 80 else ""),
                "subtitle": f"{item.item_type} on project #{item.project_id}",
                "timestamp": item.timestamp,
                "href": f"/projects/{item.project_id}/view",
            })

        for item in notification_service.get_recent_items(6):
            items.append({
                "source": "Courier",
                "category": "Notifications",
                "title": f"{item.notification_type.upper()} notification sent",
                "subtitle": item.notification_data,
                "timestamp": item.created_at,
                "href": "/processes",
            })

        for item in event_service.get_recent_items(20):
            if item.event_type == "skill:level_up":
                continue

            items.append({
                "source": "Events",
                "category": self._categorize_event(item),
                "title": item.description or item.event_type,
                "subtitle": item.event_type,
                "timestamp": item.timestamp,
                "href": "/events/home",
            })

        items.sort(key=lambda item: self._normalize_datetime(item.get("timestamp")), reverse=True)
        return [
            {
                **item,
                "timestamp": self._normalize_datetime(item.get("timestamp")).isoformat() if self._normalize_datetime(item.get("timestamp")) else None
            }
            for item in items[:limit]
        ]

    def _categorize_event(self, event) -> str:
        tags = set(event.tags or [])
        if event.event_type.startswith("project:") or "progress" in tags:
            return "Projects"
        if event.event_type.startswith("device:") or "device" in tags:
            return "Devices"
        if event.event_type.startswith("skill:") or "skill" in tags:
            return "Growth"
        if "notification" in tags or "email" in tags:
            return "Notifications"
        if "activity" in event.event_type or any(tag.startswith("triggered_by:activity:") for tag in tags):
            return "Activity"
        return "Events"

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
