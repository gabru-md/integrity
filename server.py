import os
from datetime import datetime
from apps.contracts import contracts_app
from apps.devices import devices_app
from apps.events import events_app
from apps.shortcuts import shortcuts_app
from apps.thoughts import thoughts_app
from gabru.flask.server import Server

if __name__ == '__main__':
    basedir = os.path.dirname(__file__)
    server = Server("Rasbhari", template_folder=os.path.join(basedir, "templates"),
                    static_folder=os.path.join(basedir, "static"))


    @server.app.template_filter("datetimeformat")
    def datetimeformat(value):
        try:
            if isinstance(value, (int, float)):
                return datetime.fromtimestamp(value).strftime("%b %d, %Y %H:%M")
            # ISO string
            return datetime.fromisoformat(value.replace("Z", "")).strftime("%b %d, %Y %H:%M")
        except Exception as _:
            return value


    server.register_app(contracts_app)
    server.register_app(events_app)
    server.register_app(thoughts_app)
    server.register_app(shortcuts_app)
    server.register_app(devices_app)

    # start process manager to run important processes for apps
    server.start_process_manager()

    server.run()
