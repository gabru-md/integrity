from flask import Flask, render_template
from gabru.log import Logger
from gabru.app import App
import os


class Server:
    def __init__(self, name: str, template_folder="templates"):
        self.name = name
        self.app = Flask(__name__, template_folder=template_folder)
        self.setup_default_routes()
        self.not_allowed_app_names = []
        self.log = Logger.get_log(self.name)
        self.registered_apps = []

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

    def get_widgets_data(self) -> {}:
        widgets_data = {}
        for app in self.registered_apps:
            app: App = app
            widget_data = app.widget_data()
            widgets_data[app.name.capitalize()] = widget_data
        print(widgets_data)
        return widgets_data
