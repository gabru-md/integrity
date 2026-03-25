import os
from datetime import datetime

from flask import redirect

from apps.devices import devices_app
from apps.events import events_app
from apps.thoughts import thoughts_app
from apps.projects import project_app
from apps.promises import promises_app
from apps.blogs import blog_app
from gabru.flask.server import Server
from gabru.flask.util import render_flask_template

basedir = os.path.dirname(__file__)


class RasbhariServer(Server):
    def __init__(self):
        super().__init__("Rasbhari", template_folder=os.path.join(basedir, "templates"),
                         static_folder=os.path.join(basedir, "static"))
        self.setup_datetime_filter()
        self.setup_apps()
        self.setup_additional_routes()
        self.open_webui_url = os.getenv('OPEN_WEBUI_URL')

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
        self.register_app(blog_app)
        self.register_app(promises_app)
        self.register_app(events_app)
        self.register_app(thoughts_app)
        self.register_app(devices_app)
        self.register_app(project_app)


    def run_server(self):
        # start process manager to run important processes for apps
        self.start_process_manager()
        self.run()

    def setup_additional_routes(self):
        @self.app.route('/heimdall')
        def show_heimdall_dashboard():
            return render_flask_template('heimdall.html')

        @self.app.route('/chat')
        def show_open_webui():
            return redirect(self.open_webui_url), 302


if __name__ == '__main__':
    server = RasbhariServer()
    server.run_server()
