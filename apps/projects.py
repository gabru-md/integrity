from gabru.flask.app import App
from model.project import Project
from services.projects import ProjectService
from processes.project_updater import ProjectUpdater

project_app = App(
    'Projects',
    service=ProjectService(),
    model_class=Project,
    widget_enabled=True,
    get_recent_limit=10
)

project_app.register_process(ProjectUpdater, enabled=True)

