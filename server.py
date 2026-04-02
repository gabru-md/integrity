import os
from datetime import datetime

from flask import redirect

from apps.devices import devices_app
from apps.events import events_app
from apps.thoughts import thoughts_app
from apps.projects import project_app
from apps.promises import promises_app
from apps.blogs import blog_app
from apps.activities import activities_app
from apps.kanban_tickets import kanban_tickets_app
from apps.connections import connections_app
from apps.reports import reports_app
from apps.skills import skills_app
from apps.users import users_app
from gabru.auth import login_required
from gabru.flask.server import Server
from gabru.flask.util import render_flask_template
from runtime.providers import (
    RasbhariAppStatusStore,
    RasbhariAssistantCommandProvider,
    RasbhariAuthProvider,
    RasbhariDashboardDataProvider,
)
from services.docs import DocsService

basedir = os.path.dirname(__file__)


class RasbhariServer(Server):
    def __init__(self):
        super().__init__(
            "Rasbhari",
            template_folder=os.path.join(basedir, "templates"),
            static_folder=os.path.join(basedir, "static"),
            auth_provider=RasbhariAuthProvider(),
            app_status_store=RasbhariAppStatusStore(),
            dashboard_provider=RasbhariDashboardDataProvider(),
            assistant_provider=RasbhariAssistantCommandProvider(),
        )
        self.setup_datetime_filter()
        self.setup_apps()
        self.setup_additional_routes()
        self.open_webui_url = os.getenv('OPEN_WEBUI_URL')

    def setup_datetime_filter(self):
        def _format_datetime_value(value, fmt: str):
            if isinstance(value, (int, float)):
                parsed = datetime.fromtimestamp(value)
            elif isinstance(value, str):
                try:
                    parsed = datetime.fromisoformat(value.replace("Z", ""))
                except Exception:
                    return value
            else:
                parsed = value
            formatted = parsed.strftime(fmt)
            return formatted.replace(" 0", " ").replace(" 00:", " 12:")

        @self.app.template_filter("datetimeformat")
        def datetimeformat(value):
            try:
                return _format_datetime_value(value, "%b %d, %Y %H:%M")
            except Exception as _:
                return value

        @self.app.template_filter("projectdatetimeformat")
        def projectdatetimeformat(value):
            try:
                return _format_datetime_value(value, "%b %d, %Y, %I:%M %p")
            except Exception as _:
                return value

    def setup_apps(self):
        self.register_app(blog_app)
        self.register_app(promises_app)
        self.register_app(events_app)
        self.register_app(thoughts_app)
        self.register_app(devices_app)
        self.register_app(project_app)
        self.register_app(kanban_tickets_app)
        self.register_app(activities_app)
        self.register_app(skills_app)
        self.register_app(connections_app)
        self.register_app(reports_app)
        self.register_app(users_app)


    def run_server(self):
        # start process manager to run important processes for apps
        self.start_process_manager()
        self.run()

    def setup_additional_routes(self):
        docs_service = DocsService(os.path.join(basedir, "docs"))

        @self.app.route('/chat')
        @login_required
        def show_open_webui():
            return redirect(self.open_webui_url), 302

        @self.app.route('/docs')
        @login_required
        def show_docs():
            docs = docs_service.list_docs()
            selected_path = 'README.md'
            selected_doc = docs_service.get_doc(selected_path)
            return render_flask_template('docs.html', docs=docs, selected_doc=selected_doc, selected_path=selected_path)

        @self.app.route('/docs/<path:doc_path>')
        @login_required
        def show_doc(doc_path):
            docs = docs_service.list_docs()
            selected_doc = docs_service.get_doc(doc_path)
            if selected_doc is None:
                return render_flask_template('docs.html', docs=docs, selected_doc=None, selected_path=doc_path), 404
            return render_flask_template('docs.html', docs=docs, selected_doc=selected_doc, selected_path=doc_path)


if __name__ == '__main__':
    server = RasbhariServer()
    server.run_server()
