import json

from apps.user_docs import build_app_user_guidance
from gabru.auth import PermissionManager
from gabru.flask.app import App
from model.browser_rule import BrowserRule
from services.browser_actions import BrowserActionService
from services.browser_rules import BrowserRuleService


def process_browser_rule_data(json_data):
    if "payload_mapping" in json_data and isinstance(json_data["payload_mapping"], str):
        try:
            json_data["payload_mapping"] = json.loads(json_data["payload_mapping"])
        except json.JSONDecodeError:
            json_data["payload_mapping"] = {}
    elif "payload_mapping" not in json_data or json_data["payload_mapping"] is None:
        json_data["payload_mapping"] = {}

    if "domain_in" in json_data and isinstance(json_data["domain_in"], str):
        json_data["domain_in"] = [item.strip() for item in json_data["domain_in"].split(",") if item.strip()]
    elif "domain_in" not in json_data or json_data["domain_in"] is None:
        json_data["domain_in"] = []

    for key in ("browser_action_id", "active_duration_seconds", "priority"):
        value = json_data.get(key)
        if value in ("", None):
            json_data[key] = None if key != "priority" else 100
            continue
        try:
            json_data[key] = int(value)
        except (TypeError, ValueError):
            json_data[key] = None if key != "priority" else 100

    return json_data


browser_rules_app = App(
    "BrowserRules",
    BrowserRuleService(),
    BrowserRule,
    _process_model_data_func=process_browser_rule_data,
    get_recent_limit=20,
    home_template="browser_rules.html",
    widget_enabled=False,
    user_guidance=build_app_user_guidance("BrowserRules"),
)

browser_action_service = BrowserActionService()


def get_browser_rules_home_context():
    user_id = PermissionManager.get_current_user_id()
    browser_action_options = []

    if user_id:
        for action in browser_action_service.find_all(sort_by={"name": "ASC"}):
            browser_action_options.append({
                "value": action.id,
                "label": f"{action.name} ({action.browser_action} -> {action.target_type})",
            })

    runtime_form_options = {
        "browser_action_id": [{"value": "", "label": "Choose Browser Action"}] + browser_action_options,
    }
    return {"runtime_form_options": runtime_form_options}


browser_rules_app.get_home_context = get_browser_rules_home_context
