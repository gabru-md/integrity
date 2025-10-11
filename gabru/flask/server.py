import threading

from flask import Flask, render_template, redirect, send_from_directory
from gabru.log import Logger
from gabru.flask.app import App
import os

from gabru.process import Process
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

    def get_processes_data(self) -> []:
        processes_data = []
        for app in self.registered_apps:
            app: App = app
            for process in app.get_processes():
                if isinstance(process, QueueProcessor):
                    process: QueueProcessor = process
                    process_data = {
                        'name': process.q_stats.name,
                        'type': 'QueueProcessor',
                        'is_alive': process.is_alive(),
                        'last_consumed_id': process.q_stats.last_consumed_id,
                        'owner_app': app.name
                    }
                else:
                    process: Process = process
                    process_data = {
                        'name': process.name,
                        'is_alive': process.is_alive(),
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
                'processes': app.processes
            }
            apps_data.append(app_data)
        return apps_data

    def get_widgets_data(self) -> {}:
        widgets_data = {}
        for app in self.registered_apps:
            app: App = app
            widget_data, model_class_attributes = app.widget_data()
            widgets_data[app.name.capitalize()] = (widget_data, model_class_attributes)
        return widgets_data

    def process_manager_init(self):
        processes_to_start = {}
        self.log.info(f"Starting process manager for {self.name}")
        for app in self.registered_apps:
            app: App = app
            app_processes = app.get_enabled_processes()
            if len(app_processes) > 0:
                processes_to_start[app.name] = app_processes
        self.log.info(f"Loaded all processes to run")

        _process_threads = []

        for app_name, processes in processes_to_start.items():
            for process in processes:
                process: threading.Thread = process
                self.log.info(f"Starting {process.name} for {app_name}")
                process.start()
                _process_threads.append(process)

        self.log.info(f"{len(_process_threads)} processes started, waiting for them to end.")
        for process_thread in _process_threads:
            process_thread.join()

        self.log.info("All processes concluded.")

    def start_process_manager(self):
        self.process_manager = threading.Thread(target=self.process_manager_init, daemon=True)
        self.process_manager.start()
