import threading

from flask import Flask, render_template, redirect, send_from_directory, jsonify
from gabru.log import Logger
from gabru.flask.app import App
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
        self.setup_default_routes()
        self.not_allowed_app_names = []
        self.log = Logger.get_log(self.name)
        self.registered_apps = []
        self.process_manager = None
        self.process_manager_thread = None

    def register_app(self, app: App):
        if app.name.lower() in self.not_allowed_app_names:
            raise Exception("Could not register app")

        self.registered_apps.append(app)
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

        @self.app.route('/apps')
        def apps():
            apps_data = self.get_apps_data()
            return render_template('apps.html', apps_data=apps_data)

        @self.app.route('/processes')
        def processes():
            processes_data = self.get_processes_data()
            return render_template('processes.html', processes_data=processes_data)

        @self.app.route('/shortcuts')
        def shortcuts():
            return redirect('shortcuts/home'), 302

        @self.app.route('/download/<filename>')
        def download(filename):
            return send_from_directory(directory=SERVER_FILES_FOLDER, path=filename, as_attachment=True)

        @self.app.route('/enable_process/<process_name>', methods=['POST'])
        def enable_process(process_name):
            if self.process_manager:
                process_manager: ProcessManager = self.process_manager
                success = process_manager.enable_process(process_name)
                if success:
                    return jsonify({"message": f"Process {process_name} enabled successfully"}), 200
                else:
                    return jsonify({"error": f"Failed to enable process {process_name}. Check logs for details."}), 500
            return jsonify({"error": "Process Manager is not initialized"}), 500

        @self.app.route('/disable_process/<process_name>', methods=['POST'])
        def disable_process(process_name):
            if self.process_manager:
                process_manager: ProcessManager = self.process_manager
                success = process_manager.disable_process(process_name)
                if success:
                    return jsonify({"message": f"Process {process_name} disabled successfully"}), 200
                else:
                    return jsonify({"error": f"Failed to disable process {process_name}. Check logs for details."}), 500
            return jsonify({"error": "Process Manager is not initialized"}), 500

        @self.app.route('/start_process/<process_name>', methods=['POST'])
        def start_process(process_name):
            if self.process_manager:
                process_manager: ProcessManager = self.process_manager
                success = process_manager.run_process(process_name)
                if success:
                    return jsonify({"message": f"Process {process_name} started successfully"}), 200
                else:
                    return jsonify({
                                       "error": f"Failed to start process {process_name}. It might be disabled or already running."}), 500
            return jsonify({"error": "Process Manager is not initialized"}), 500

        @self.app.route('/stop_process/<process_name>', methods=['POST'])
        def stop_process(process_name):
            if self.process_manager:
                process_manager: ProcessManager = self.process_manager
                process_manager.pause_process(process_name)
                return jsonify({"message": f"Process {process_name} stopped successfully"}), 200
            return jsonify({"error": "Process Manager is not initialized"}), 500

    def get_processes_data(self) -> list:
        processes_data = []
        process_manager: ProcessManager = self.process_manager

        for app in self.registered_apps:
            app: App = app

            for blueprint in app.get_processes():

                # Extract the process class and kwargs from the blueprint
                process_class, args, kwargs = blueprint

                process_name = kwargs.get('name', process_class.__name__)
                is_alive = False
                is_enabled = kwargs.get('enabled', False)

                # Get the current INSTANCE from the ProcessManager's map
                process_instance = process_manager.all_processes_map.get(process_name) if process_manager else None

                # retrieve actual live status and enabled state from the instance/manager
                if process_manager and process_instance:
                    is_alive = process_manager.get_process_status(process_name)
                    is_enabled = process_instance.enabled

                # Check the *class* type, not the instance (which might not exist)
                if issubclass(process_class, QueueProcessor):  # Assuming QueueProcessor is the class name

                    last_consumed_id = process_instance.q_stats.last_consumed_id if process_instance and hasattr(
                        process_instance, 'q_stats') else None

                    process_data = {
                        'name': process_name,
                        'type': 'QueueProcessor',
                        'is_alive': is_alive,
                        'is_enabled': is_enabled,
                        'last_consumed_id': last_consumed_id,
                        'owner_app': app.name
                    }
                else:
                    process_data = {
                        'name': process_name,
                        'is_alive': is_alive,
                        'is_enabled': is_enabled,
                        'owner_app': app.name,
                        'type': 'Process',
                        'last_consumed_id': None
                    }
                processes_data.append(process_data)

        return processes_data

    def get_apps_data(self) -> []:
        apps_data = []
        for app in self.registered_apps:
            app: App = app
            app_data = {
                'name': app.name,
                'model_class': app.model_class.__name__,
                'processes': app.processes,
                'widget_enabled': app.widget_enabled,
                'model_class_attributes': app.model_class_attributes
            }
            apps_data.append(app_data)
        return apps_data

    def get_widgets_data(self) -> {}:
        widgets_data = {}
        for app in self.registered_apps:
            app: App = app
            widget_data, model_class_attributes = app.widget_data()
            if widget_data:
                widgets_data[app.name.capitalize()] = (widget_data, model_class_attributes)
        return widgets_data

    def process_manager_init(self):
        # Now pass ALL processes to the ProcessManager
        processes_to_manage = {}
        self.log.info(f"Starting process manager for {self.name}")

        for app in self.registered_apps:
            app: App = app
            # Get ALL processes, not just enabled ones
            app_processes = app.get_processes()
            if len(app_processes) > 0:
                processes_to_manage[app.name] = app_processes

        self.log.info(f"Loaded all processes to manage")

        # Pass ALL processes to the ProcessManager
        self.process_manager = ProcessManager(processes_to_manage=processes_to_manage)

        self.process_manager.start()
        self.process_manager.join()

        self.log.info("All processes concluded.")

    def start_process_manager(self):
        self.process_manager_thread = threading.Thread(target=self.process_manager_init, daemon=True)
        self.process_manager_thread.start()