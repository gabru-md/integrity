import os
from datetime import datetime

from flask import render_template

from apps.contracts import contracts_app
from apps.devices import devices_app
from apps.events import events_app
from apps.shortcuts import shortcuts_app
from apps.thoughts import thoughts_app
from gabru.flask.server import Server

basedir = os.path.dirname(__file__)


class RasbhariServer(Server):
    def __init__(self):
        super().__init__("Rasbhari", template_folder=os.path.join(basedir, "templates"),
                         static_folder=os.path.join(basedir, "static"))
        self.setup_datetime_filter()
        self.setup_apps()
        self.setup_additional_routes()

    def setup_datetime_filter(self):
        @self.app.template_filter("datetimeformat")
        def datetimeformat(value):
            try:
                if isinstance(value, (int, float)):
                    return datetime.fromtimestamp(value).strftime("%b %d, %Y %H:%M")
                # ISO string
                return datetime.fromisoformat(value.replace("Z", "")).strftime("%b %d, %Y %H:%M")
            except Exception as _:
                return value

    def setup_apps(self):
        self.register_app(contracts_app)
        self.register_app(events_app)
        self.register_app(thoughts_app)
        self.register_app(shortcuts_app)
        self.register_app(devices_app)

    def run_server(self):
        # start process manager to run important processes for apps
        self.start_process_manager()
        self.run()

    def setup_additional_routes(self):
        @self.app.route('/heimdall')
        def show_heimdall_dashboard():
            return render_template('heimdall.html')


if __name__ == '__main__':
    server = RasbhariServer()
    server.run_server()
