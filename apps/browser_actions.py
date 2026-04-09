import json

from apps.user_docs import build_app_user_guidance
from gabru.auth import PermissionManager
from gabru.flask.app import App
from services.activities import ActivityService
from model.browser_action import BrowserAction
from services.browser_actions import BrowserActionService
from services.projects import ProjectService


def process_browser_action_data(json_data):
    if "default_payload" in json_data and isinstance(json_data["default_payload"], str):
        try:
            json_data["default_payload"] = json.loads(json_data["default_payload"])
        except json.JSONDecodeError:
            json_data["default_payload"] = {}
    elif "default_payload" not in json_data or json_data["default_payload"] is None:
        json_data["default_payload"] = {}

    if "target_tags" in json_data and isinstance(json_data["target_tags"], str):
        json_data["target_tags"] = [tag.strip() for tag in json_data["target_tags"].split(",") if tag.strip()]
    elif "target_tags" not in json_data or json_data["target_tags"] is None:
        json_data["target_tags"] = []

    for key in ("target_activity_id", "target_project_id"):
        value = json_data.get(key)
        if value in ("", None):
            json_data[key] = None
            continue
        try:
            json_data[key] = int(value)
        except (TypeError, ValueError):
            json_data[key] = None

    return json_data


browser_actions_app = App(
    "BrowserActions",
    BrowserActionService(),
    BrowserAction,
    _process_model_data_func=process_browser_action_data,
    get_recent_limit=20,
    home_template="browser_actions.html",
    widget_enabled=False,
    user_guidance=build_app_user_guidance("BrowserActions"),
)

activity_service = ActivityService()
project_service = ProjectService()


def get_browser_actions_home_context():
    user_id = PermissionManager.get_current_user_id()
    activity_options = []
    project_options = []

    if user_id:
        for activity in activity_service.find_all(sort_by={"name": "ASC"}):
            activity_options.append({
                "value": activity.id,
                "label": f"{activity.name} ({activity.event_type})",
            })
        for project in project_service.find_all(sort_by={"name": "ASC"}):
            project_options.append({
                "value": project.id,
                "label": project.name,
            })

    runtime_form_options = {
        "target_activity_id": [{"value": "", "label": "No linked activity"}] + activity_options,
        "target_project_id": [{"value": "", "label": "No linked project"}] + project_options,
    }
    return {"runtime_form_options": runtime_form_options}


browser_actions_app.get_home_context = get_browser_actions_home_context
