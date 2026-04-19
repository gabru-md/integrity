from datetime import datetime
from typing import Any

from flask import Blueprint, jsonify, request

from gabru.auth import PermissionManager, login_required
from model.event import Event
from services.events import EventService


home_assistant_blueprint = Blueprint("home_assistant_integration", __name__, url_prefix="/integrations/home-assistant")
event_service = EventService()


def _normalize_tags(value: Any) -> list[str]:
    if isinstance(value, str):
        raw_tags = value.split(",")
    elif isinstance(value, list):
        raw_tags = value
    else:
        raw_tags = []

    normalized = []
    for tag in raw_tags:
        tag_value = str(tag).strip()
        if tag_value and tag_value not in normalized:
            normalized.append(tag_value)
    return normalized


def _with_required_home_assistant_tags(tags: list[str]) -> list[str]:
    required_tags = ["home", "source:home_assistant", "integration:home_assistant"]
    enriched = list(tags)
    for tag in required_tags:
        if tag not in enriched:
            enriched.append(tag)
    return enriched


@home_assistant_blueprint.route("/events", methods=["POST"])
@login_required
def ingest_event():
    data = request.get_json(silent=True)
    if not isinstance(data, dict):
        return jsonify({"error": "JSON request body is required"}), 400

    event_type = str(data.get("event_type") or "").strip()
    if not event_type:
        return jsonify({"error": "event_type is required"}), 400

    description = str(data.get("description") or event_type).strip()
    payload = data.get("payload") if isinstance(data.get("payload"), dict) else {}
    tags = _with_required_home_assistant_tags(_normalize_tags(data.get("tags")))
    user_id = PermissionManager.get_current_user_id()
    if user_id is None:
        return jsonify({"error": "Unable to determine current user"}), 401

    event = Event(
        user_id=user_id,
        event_type=event_type,
        timestamp=datetime.now(),
        description=description,
        tags=tags,
        payload={
            **payload,
            "source": "home_assistant",
            "integration": "home_assistant",
        },
    )
    event_id = event_service.create(event)
    if not event_id:
        return jsonify({"error": "Failed to create Home Assistant event"}), 500

    return jsonify({
        "id": event_id,
        "event_type": event.event_type,
        "description": event.description,
        "tags": event.tags,
        "payload": event.payload,
    }), 201
