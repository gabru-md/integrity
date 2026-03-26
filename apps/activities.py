import json
from flask import request, jsonify

from gabru.flask.app import App
from model.activity import Activity
from services.activities import ActivityService


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

activities_app = App(
    'Activities',
    ActivityService(),
    Activity,
    _process_model_data_func=process_activity_data,
    home_template="activities.html"
)


@activities_app.blueprint.route('/trigger/<int:activity_id>', methods=['POST'])
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
