import threading

from flask import Flask, render_template, redirect, send_from_directory, jsonify, session, request, abort
from gabru.log import Logger
from gabru.flask.app import App
from gabru.auth import PermissionManager, Role, admin_required
import os

from gabru.process import ProcessManager
from gabru.qprocessor.qprocessor import QueueProcessor

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
        self.process_manager = None
        self.process_manager_thread = None

    def setup_auth_context(self):
        @self.app.context_processor
        def inject_permissions():
            return dict(
                PermissionManager=PermissionManager,
                current_role=PermissionManager.get_current_role(),
                Role=Role
            )

    def register_app(self, app: App):
        if app.name.lower() in self.not_allowed_app_names:
            raise Exception("Could not register app")

        self.registered_apps.append(app)
        app.server_instance = self # give it the server instance
        self.app.register_blueprint(app.blueprint, url_prefix=f"/{app.name.lower()}")

    def run(self):
        self.app.run(
            debug=os.getenv("SERVER_DEBUG", False),
            host='0.0.0.0',
            port=os.getenv("SERVER_PORT", 5000)
        )

    def setup_default_routes(self):
        @self.app.route('/')
        def home():
            widgets_data = self.get_widgets_data()
            return render_template('home.html', widgets_data=widgets_data)

        @self.app.route('/set_role/<role_name>', methods=['POST'])
        def set_role(role_name):
            try:
                role = Role(role_name.lower())
                PermissionManager.set_role(role)
                return jsonify({"message": f"Role set to {role_name}"}), 200
            except ValueError:
                return jsonify({"error": "Invalid role"}), 400

        @self.app.route('/apps')
        @admin_required
        def apps():
            apps_data = self.get_apps_data()
            return render_template('apps.html', apps_data=apps_data)

        @self.app.route('/processes')
        @admin_required
        def processes():
            processes_data = self.get_processes_data()
            return render_template('processes.html', processes_data=processes_data)
        
        @self.app.route('/heimdall')
        @admin_required
        def heimdall():
            return render_template('heimdall.html')

        @self.app.route('/devices')
        @admin_required
        def devices():
            return redirect('/devices/home')

        @self.app.route('/download/<filename>')
        def download(filename):
            return send_from_directory(directory=SERVER_FILES_FOLDER, path=filename, as_attachment=True)

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

    def get_apps_data(self) -> []:
        apps_data = []
        for app in self.registered_apps:
            app_data = {
                'name': app.name,
                'model_class': app.model_class.__name__,
                'processes': [p[0].__name__ for p in app.processes],
                'widget_enabled': app.widget_enabled
            }
            apps_data.append(app_data)
        return apps_data

    def get_widgets_data(self) -> {}:
        widgets_data = {}
        for app in self.registered_apps:
            # Check if the current role can view the app AND if the app has its widget functionality enabled
            if PermissionManager.can_view_app(app.name):
                widget_data, model_attributes = app.widget_data()
                if widget_data:
                    widgets_data[app.name.capitalize()] = (widget_data, model_attributes)
        return widgets_data

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
        self.process_manager_thread = threading.Thread(target=self.process_manager_init, daemon=True)
        self.process_manager_thread.start()
