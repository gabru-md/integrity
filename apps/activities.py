import json
from flask import request, jsonify

from gabru.auth import write_access_required
from gabru.flask.app import App
from apps.user_docs import build_app_user_guidance
from model.activity import Activity
from services.activities import ActivityService
from services.events import EventService
from services.promises import PromiseService
from services.skills import SkillService


def process_activity_data(json_data):
    # Ensure default_payload is a dictionary
    if "default_payload" in json_data and isinstance(json_data["default_payload"], str):
        try:
            json_data["default_payload"] = json.loads(json_data["default_payload"])
        except json.JSONDecodeError:
            json_data["default_payload"] = {}
    elif "default_payload" not in json_data or json_data["default_payload"] is None:
        json_data["default_payload"] = {}

    # Handle tags: expecting comma-separated string from form, convert to list
    if "tags" in json_data and isinstance(json_data["tags"], str):
        json_data["tags"] = [tag.strip() for tag in json_data["tags"].split(',') if tag.strip()]
    elif "tags" not in json_data or json_data["tags"] is None:
        json_data["tags"] = []

    return json_data


activity_service = ActivityService()
event_service = EventService()
promise_service = PromiseService()
skill_service = SkillService()

activities_app = App(
    'Activities',
    ActivityService(),
    Activity,
    _process_model_data_func=process_activity_data,
    home_template="activities.html",
    widget_type="basic",
    user_guidance=build_app_user_guidance("Activities")
)


def _match_promises(activity: Activity) -> list[dict]:
    tag_values = {str(tag).strip().lower() for tag in (activity.tags or []) if str(tag).strip()}
    matches = []
    for promise in promise_service.find_all(sort_by={"name": "ASC"}):
        matched = False
        if promise.target_event_type and promise.target_event_type == activity.event_type:
            matched = True
        if promise.target_event_tag and promise.target_event_tag.strip().lower() in tag_values:
            matched = True
        if matched:
            matches.append({"id": promise.id, "name": promise.name, "href": "/promises/home"})
    return matches[:3]


def _match_skills(activity: Activity) -> list[dict]:
    normalized_tags = {
        SkillService.normalize_skill_tag(str(tag))
        for tag in (activity.tags or [])
        if str(tag).strip()
    }
    matches = []
    for skill in skill_service.find_all(sort_by={"name": "ASC"}):
        if skill_service.get_match_keys(skill).intersection(normalized_tags):
            matches.append({"id": skill.id, "name": skill.name, "href": "/skills/home"})
    return matches[:3]


def _serialize_activity(activity: Activity) -> dict:
    recent_events = event_service.find_all(filters={"event_type": activity.event_type}, sort_by={"timestamp": "DESC"})
    latest_event = recent_events[0] if recent_events else None
    linked_promises = _match_promises(activity)
    linked_skills = _match_skills(activity)
    payload_keys = sorted((activity.default_payload or {}).keys())
    activity_data = activity.dict()
    activity_data["event_summary"] = f"{activity.event_type} · {len(activity.tags or [])} tag{'s' if len(activity.tags or []) != 1 else ''}"
    activity_data["linked_promises"] = linked_promises
    activity_data["linked_skills"] = linked_skills
    activity_data["trigger_count"] = len(recent_events)
    activity_data["latest_event"] = latest_event.dict() if latest_event else None
    activity_data["payload_keys"] = payload_keys
    return activity_data


@activities_app.blueprint.route('/catalog', methods=['GET'])
def activity_catalog():
    activities = activity_service.find_all(sort_by={"name": "ASC"})
    return jsonify([_serialize_activity(activity) for activity in activities]), 200


@activities_app.blueprint.route('/trigger/<int:activity_id>', methods=['POST'])
@write_access_required
def trigger_activity_endpoint(activity_id):
    """ Endpoint to trigger an activity and emit its corresponding event. """
    # The override_payload can come from the request body and might contain event-specific data
    # including potential tags to merge or override.
    override_data = request.json or {}
    override_payload = override_data.get('payload') # Assuming a nested payload structure

    # If override_payload is None but there's data directly in the request body,
    # use that as the override_payload.
    if override_payload is None and override_data:
        override_payload = override_data

    triggered_id = activity_service.trigger_activity(activity_id, override_payload=override_payload)

    if triggered_id:
        return jsonify({"message": f"Activity {activity_id} triggered successfully, event created.", "activity_id": triggered_id}), 200
    else:
        return jsonify({"error": f"Failed to trigger activity {activity_id}."}), 500
