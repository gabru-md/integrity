import os
from datetime import datetime
from io import BytesIO
from zipfile import ZIP_DEFLATED, ZipFile

from flask import redirect, abort, send_file

from apps.devices import devices_app
from apps.events import events_app
from apps.thoughts import thoughts_app
from apps.projects import project_app
from apps.promises import promises_app
from apps.blogs import blog_app
from apps.browser_actions import browser_actions_app
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
    RasbhariAdminOpsProvider,
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
            admin_ops_provider=RasbhariAdminOpsProvider(),
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
        self.register_app(browser_actions_app)
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

        @self.app.route('/automation')
        @login_required
        def show_automation():
            automation_docs = [
                {
                    "title": "Automation Overview",
                    "href": "/docs/automation.md",
                    "summary": "Product framing for Automation and Capture Automation."
                },
                {
                    "title": "Browser Extension Spec",
                    "href": "/docs/browser-extension-spec.md",
                    "summary": "Formal product contract for the first browser capture client."
                },
                {
                    "title": "Browser Action Model",
                    "href": "/docs/browser-actions.md",
                    "summary": "Shared browser verbs Rasbhari can map back into activities and events."
                },
                {
                    "title": "Browser Rule Model",
                    "href": "/docs/browser-rules.md",
                    "summary": "If A on B then trigger C, with scoped targets and trigger modes."
                },
                {
                    "title": "Sync And Local History",
                    "href": "/docs/browser-sync-history.md",
                    "summary": "How the extension connects, syncs config, and records what it did."
                },
                {
                    "title": "Implementation Plan",
                    "href": "/docs/browser-extension-implementation-plan.md",
                    "summary": "Chrome-first build order, v1 scope, and defer list."
                },
            ]
            automation_status = {
                "extension_delivery_ready": False,
                "chrome_extension_ready": False,
                "sync_api_ready": False,
                "notes": "This page is the home for Capture Automation. Connection and live setup status will land here as the browser extension and sync APIs ship."
            }
            return render_flask_template(
                'automation.html',
                automation_docs=automation_docs,
                automation_status=automation_status,
            )

        @self.app.route('/automation/chrome-extension.zip')
        @login_required
        def download_chrome_extension_bundle():
            extension_dir = os.path.join(basedir, "static", "automation", "chrome-extension")
            if not os.path.isdir(extension_dir):
                abort(404)

            bundle = BytesIO()
            with ZipFile(bundle, "w", ZIP_DEFLATED) as archive:
                for root, _, files in os.walk(extension_dir):
                    for filename in files:
                        full_path = os.path.join(root, filename)
                        archive_path = os.path.relpath(full_path, extension_dir)
                        archive.write(full_path, archive_path)
            bundle.seek(0)

            return send_file(
                bundle,
                mimetype="application/zip",
                as_attachment=True,
                download_name="rasbhari-chrome-extension.zip",
            )


if __name__ == '__main__':
    server = RasbhariServer()
    server.run_server()
