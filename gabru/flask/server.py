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
from gabru.qprocessor.qservice import QueueService
from gabru.flask.util import render_flask_template
from apps.user_docs import build_rasbhari_admin_guide

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

        @self.app.route('/admin/guide')
        @admin_required
        def admin_guide():
            return render_flask_template('admin_guide.html', admin_guide=build_rasbhari_admin_guide())

        @self.app.route('/admin')
        @admin_required
        def admin_overview():
            return render_flask_template('admin_overview.html', admin_data=self.get_admin_control_plane_data())

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

        @self.app.route('/restart_process/<process_name>', methods=['POST'])
        @admin_required
        def restart_process(process_name):
            if not self.process_manager:
                return jsonify({"error": "Process Manager is not initialized"}), 500

            self.process_manager.pause_process(process_name)
            success = self.process_manager.run_process(process_name)
            if success:
                return jsonify({"message": f"Process {process_name} restarted successfully"}), 200
            return jsonify({"error": f"Failed to restart process {process_name}"}), 500

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

        @self.app.route('/process_progress/<process_name>', methods=['POST'])
        @admin_required
        def update_process_progress(process_name):
            data = request.get_json(silent=True)
            if not isinstance(data, dict):
                return jsonify({"error": "JSON request body is required"}), 400

            last_consumed_id = data.get("last_consumed_id")
            try:
                last_consumed_id = int(last_consumed_id)
            except (TypeError, ValueError):
                return jsonify({"error": "last_consumed_id must be an integer"}), 400

            if last_consumed_id < 0:
                return jsonify({"error": "last_consumed_id cannot be negative"}), 400

            process_instance = self.process_manager.all_processes_map.get(process_name) if self.process_manager else None
            if process_instance is not None and not hasattr(process_instance, "q_stats"):
                return jsonify({"error": f"Process {process_name} is not a queue processor"}), 400

            if process_instance is None:
                process_type = None
                for app in self.registered_apps:
                    for p_class, _args, kwargs in app.get_processes():
                        name = kwargs.get('name', p_class.__name__)
                        if name == process_name:
                            process_type = p_class
                            break
                    if process_type is not None:
                        break
                if process_type is None:
                    return jsonify({"error": f"Process {process_name} not found"}), 404
                if not issubclass(process_type, QueueProcessor):
                    return jsonify({"error": f"Process {process_name} is not a queue processor"}), 400

            queue_service = QueueService()
            updated_stats = queue_service.set_last_consumed_id(process_name, last_consumed_id)

            if process_instance is not None:
                if hasattr(process_instance, "reload_queue_state"):
                    process_instance.reload_queue_state(last_consumed_id)
                else:
                    process_instance.q_stats.last_consumed_id = last_consumed_id

            return jsonify({
                "message": f"Updated {process_name} progress to {last_consumed_id} and reloaded runtime state",
                "process_name": process_name,
                "last_consumed_id": updated_stats.last_consumed_id,
            }), 200

        @self.app.route('/process_progress/<process_name>/latest', methods=['POST'])
        @admin_required
        def jump_process_progress_to_latest(process_name):
            process_instance = self.process_manager.all_processes_map.get(process_name) if self.process_manager else None
            if process_instance is not None and not hasattr(process_instance, "q_stats"):
                return jsonify({"error": f"Process {process_name} is not a queue processor"}), 400

            process_type = None
            if process_instance is None:
                for app in self.registered_apps:
                    for p_class, _args, kwargs in app.get_processes():
                        name = kwargs.get('name', p_class.__name__)
                        if name == process_name:
                            process_type = p_class
                            break
                    if process_type is not None:
                        break

                if process_type is None:
                    return jsonify({"error": f"Process {process_name} not found"}), 404
                if not issubclass(process_type, QueueProcessor):
                    return jsonify({"error": f"Process {process_name} is not a queue processor"}), 400

            service = process_instance.service if process_instance is not None else process_type(enabled=False, name=process_name).service
            latest_items = service.get_recent_items(limit=1)
            latest_id = latest_items[0].id if latest_items else 0

            queue_service = QueueService()
            updated_stats = queue_service.set_last_consumed_id(process_name, latest_id)

            if process_instance is not None:
                if hasattr(process_instance, "reload_queue_state"):
                    process_instance.reload_queue_state(latest_id)
                else:
                    process_instance.q_stats.last_consumed_id = latest_id

            return jsonify({
                "message": f"Moved {process_name} to latest id {latest_id}",
                "process_name": process_name,
                "last_consumed_id": updated_stats.last_consumed_id,
            }), 200

    def get_processes_data(self) -> list:
        processes_data = []
        if not self.process_manager: return []
        for app in self.registered_apps:
            for p_class, args, kwargs in app.get_processes():
                name = kwargs.get('name', p_class.__name__)
                instance = self.process_manager.all_processes_map.get(name)
                is_alive = self.process_manager.get_process_status(name) if instance else False
                is_enabled = instance.enabled if instance else kwargs.get('enabled', False)
                
                p_data = {
                    'name': name,
                    'is_alive': is_alive,
                    'is_enabled': is_enabled,
                    'owner_app': app.name,
                }
                if issubclass(p_class, QueueProcessor) and instance:
                    p_data.update({
                        'type': 'QueueProcessor',
                        'last_consumed_id': getattr(instance.q_stats, 'last_consumed_id', None),
                        'recovery_summary': 'Replay, jump, and restart controls available.',
                    })
                else:
                    p_data.update({
                        'type': 'Process',
                        'last_consumed_id': None,
                        'recovery_summary': 'Restart and log inspection available.',
                    })
                p_data['status_label'] = 'Running' if is_alive else ('Disabled' if not is_enabled else 'Stopped')
                p_data['health_state'] = 'healthy' if is_alive else ('idle' if not is_enabled else 'attention')
                processes_data.append(p_data)
        return processes_data

    def get_dependency_health_data(self) -> list[dict]:
        if not self.dashboard_provider:
            return []
        return self.dashboard_provider.get_dependency_health_data()

    def get_apps_data(self) -> []:
        processes_by_app = {}
        for process in self.get_processes_data():
            processes_by_app.setdefault(process.get("owner_app"), []).append(process)

        apps_data = []
        for app in self.registered_apps:
            app_processes = processes_by_app.get(app.name, [])
            guidance = getattr(app, "user_guidance", {}) or {}
            ecosystem_fit = guidance.get("ecosystem_fit") or {}
            enabled_processes = [process for process in app_processes if process.get("is_enabled")]
            stopped_enabled_processes = [
                process for process in app_processes
                if process.get("is_enabled") and not process.get("is_alive")
            ]
            running_processes = [process for process in app_processes if process.get("is_alive")]
            queue_processors = [process for process in app_processes if process.get("type") == "QueueProcessor"]
            if not app.is_active:
                health_state = "inactive"
            elif stopped_enabled_processes:
                health_state = "attention"
            elif app_processes:
                health_state = "healthy" if len(running_processes) == len(enabled_processes) else "mixed"
            else:
                health_state = "steady"

            app_data = {
                'name': app.name,
                'model_class': app.model_class.__name__,
                'home_href': f"/{app.name.lower()}/home",
                'route_prefix': f"/{app.name.lower()}",
                'owned_resource_label': f"{app.model_class.__name__} records",
                'ownership_summary': f"Owns the {app.model_class.__name__} resource and its primary UI surface.",
                'purpose': guidance.get("app_purpose") or guidance.get("overview") or "",
                'pairs_with': guidance.get("pairs_with", []),
                'setup_leverage': guidance.get("setup_leverage", []),
                'ecosystem_summary': ecosystem_fit.get("summary", ""),
                'ecosystem_stages': ecosystem_fit.get("stages", []),
                'processes': app_processes,
                'process_count': len(app_processes),
                'running_process_count': len(running_processes),
                'enabled_process_count': len(enabled_processes),
                'queue_process_count': len(queue_processors),
                'stopped_enabled_process_count': len(stopped_enabled_processes),
                'process_summary': (
                    f"{len(app_processes)} background worker{'s' if len(app_processes) != 1 else ''} registered"
                    if app_processes else "No background workers registered"
                ),
                'widget_type': getattr(app, "widget_type", "basic"),
                'widget_enabled': app.widget_enabled,
                'widget_summary': (
                    f"{app.widget_type.replace('_', ' ').title()} widget enabled in the dashboard"
                    if app.widget_enabled else "No active dashboard widget"
                ),
                'is_active': app.is_active,
                'health_state': health_state,
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

    def get_admin_control_plane_data(self) -> dict:
        apps_data = self.get_apps_data()
        processes_data = self.get_processes_data()
        dependency_health_data = self.get_dependency_health_data()
        admin_health = self.dashboard_provider.get_admin_health_data(processes_data) if self.dashboard_provider else {
            "checked_at": None,
            "checked_at_display": "unknown",
            "host": "unknown",
            "server": {"status": "Healthy", "summary": "Admin surface reachable now", "detail": ""},
            "event_flow": {"status": "Paused", "summary": "No event data", "detail": ""},
            "queue_drift": {"status": "Paused", "summary": "No queue data", "detail": "", "processors": []},
            "dependencies": {"status": "Paused", "summary": "No dependency data", "detail": ""},
            "reliability_cards": [],
        }

        users_app = next((app for app in self.registered_apps if app.name.lower() == "users" and getattr(app, "is_active", False)), None)
        pending_approvals = 0
        total_users = 0
        active_users = 0
        if users_app and getattr(users_app, "service", None):
            try:
                pending_approvals = users_app.service.count(filters={"is_approved": False})
                total_users = users_app.service.count()
                active_users = users_app.service.count(filters={"is_active": True})
            except Exception:
                pending_approvals = 0
                total_users = 0
                active_users = 0

        active_apps = [app for app in apps_data if app.get("is_active")]
        inactive_apps = [app for app in apps_data if not app.get("is_active")]
        enabled_processes = [process for process in processes_data if process.get("is_enabled")]
        running_processes = [process for process in processes_data if process.get("is_alive")]
        stopped_enabled_processes = [process for process in processes_data if process.get("is_enabled") and not process.get("is_alive")]
        queue_processors = [process for process in processes_data if process.get("type") == "QueueProcessor"]
        unhealthy_dependencies = [item for item in dependency_health_data if item.get("status") not in {"Healthy", "Configured"}]
        apps_needing_attention = [app for app in apps_data if app.get("health_state") == "attention"]
        disabled_widget_apps = [app for app in active_apps if not app.get("widget_enabled")]
        degraded_capabilities = []
        operator_issues = []

        if pending_approvals:
            degraded_capabilities.append({
                "title": "User onboarding is blocked",
                "body": f"{pending_approvals} user account(s) are waiting for approval, which slows first-run momentum.",
                "href": "/users/home",
                "severity": "attention",
            })
            operator_issues.append({
                "title": "Pending approvals",
                "body": f"{pending_approvals} account(s) are waiting for admin action.",
                "href": "/users/home",
            })

        if stopped_enabled_processes:
            degraded_capabilities.append({
                "title": "Background automation is degraded",
                "body": f"{len(stopped_enabled_processes)} enabled process(es) are stopped, so parts of the event loop are not advancing.",
                "href": "/processes",
                "severity": "danger",
            })
            operator_issues.append({
                "title": "Stopped enabled processors",
                "body": f"{len(stopped_enabled_processes)} enabled processor(s) need restart or replay.",
                "href": "/processes",
            })

        if unhealthy_dependencies:
            degraded_capabilities.append({
                "title": "External integrations are degraded",
                "body": f"{len(unhealthy_dependencies)} dependency check(s) are unhealthy, which may suppress notifications or AI-assisted flows.",
                "href": "/processes",
                "severity": "attention",
            })
            operator_issues.append({
                "title": "Dependency issues",
                "body": f"{len(unhealthy_dependencies)} integration dependency issue(s) need attention.",
                "href": "/processes",
            })

        if apps_needing_attention:
            degraded_capabilities.append({
                "title": "Some app-owned workers need attention",
                "body": f"{len(apps_needing_attention)} app surface(s) have enabled workers that are not healthy.",
                "href": "/apps",
                "severity": "attention",
            })

        if not active_apps:
            degraded_capabilities.append({
                "title": "No product apps are active",
                "body": "Rasbhari cannot function as an ecosystem until at least one app surface is enabled.",
                "href": "/apps",
                "severity": "danger",
            })

        if not unhealthy_dependencies and not stopped_enabled_processes and not pending_approvals:
            operator_issues.append({
                "title": "Control plane is calm",
                "body": "No high-signal operator interruptions are surfaced right now.",
                "href": "/admin",
            })

        stuck_processors = []
        for process in stopped_enabled_processes:
            last_consumed_id = process.get("last_consumed_id")
            if last_consumed_id is None:
                summary = "Enabled but stopped"
            else:
                summary = f"Stopped at queue item {last_consumed_id}"
            stuck_processors.append({
                "name": process.get("name"),
                "owner_app": process.get("owner_app"),
                "summary": summary,
                "href": "/processes",
            })

        return {
            "headline": "Admin Control Plane",
            "summary": "Use Rasbhari itself to operate the Rasbhari ecosystem: inspect health, spot degraded capabilities, resolve approvals, and recover processes before users feel the drift.",
            "metrics": [
                {"label": "Server", "value": admin_health["server"]["status"], "detail": f"{admin_health['host']} · {admin_health['checked_at_display']}"},
                {"label": "Active Apps", "value": len(active_apps), "detail": f"{len(inactive_apps)} disabled"},
                {"label": "Running Processes", "value": len(running_processes), "detail": f"{len(stopped_enabled_processes)} enabled but stopped"},
                {"label": "Users", "value": total_users, "detail": f"{pending_approvals} pending approval"},
                {"label": "Queue Drift", "value": admin_health["queue_drift"]["summary"], "detail": admin_health["queue_drift"]["status"]},
                {"label": "Dependencies", "value": admin_health["dependencies"]["summary"], "detail": admin_health["dependencies"]["status"]},
            ],
            "focus_areas": [
                {
                    "title": "App Registry",
                    "summary": "Control which product surfaces are active, what they own, and whether their widgets participate in the shell.",
                    "items": [
                        f"{len(active_apps)} apps currently active",
                        f"{len(inactive_apps)} apps currently disabled",
                        f"{len(disabled_widget_apps)} active app(s) hidden from the dashboard",
                    ],
                    "href": "/apps",
                    "action_label": "Open App Registry",
                },
                {
                    "title": "Process Runtime",
                    "summary": "Operate background workers, inspect queue progress, and recover from drift without leaving Rasbhari.",
                    "items": [
                        f"{len(running_processes)} processes currently running",
                        f"{len(queue_processors)} queue processors with replayable progress",
                        f"{len(stopped_enabled_processes)} enabled process(es) currently stopped",
                    ],
                    "href": "/processes",
                    "action_label": "Open Processes",
                },
                {
                    "title": "User Stewardship",
                    "summary": "Approve new users, monitor onboarding readiness, and keep operator access tight.",
                    "items": [
                        f"{total_users} total user accounts",
                        f"{pending_approvals} approvals waiting",
                    ],
                    "href": "/users/home",
                    "action_label": "Open Users",
                },
                {
                    "title": "Operational Boundaries",
                    "summary": "Use Rasbhari for product operations. Keep host-level repair outside the product.",
                    "items": [
                        "Inside Rasbhari: apps, widgets, processes, queue recovery, approvals, and dependency checks",
                        "Outside Rasbhari: database repair, container/service restarts, backups, and filesystem work",
                    ],
                    "href": "/admin/guide",
                    "action_label": "Open Admin Guide",
                },
            ],
            "attention_items": operator_issues,
            "degraded_capabilities": degraded_capabilities,
            "stuck_processors": stuck_processors,
            "inactive_apps": [
                {
                    "name": app.get("name"),
                    "href": app.get("home_href"),
                    "summary": app.get("purpose") or "Currently disabled.",
                }
                for app in inactive_apps[:5]
            ],
            "pending_approvals": pending_approvals,
            "dependency_health": dependency_health_data[:4],
            "recent_queue_processors": queue_processors[:5],
            "admin_health": admin_health,
        }

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
