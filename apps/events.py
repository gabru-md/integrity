from flask import Blueprint, jsonify, render_template, request

from gabru.log import Logger
from model.event import Event
from services.events import EventService
from datetime import datetime

events_app = Blueprint('events', __name__)
events_service = EventService()

log = Logger.get_log('Events')


@events_app.route('/')
def get_events():
    try:
        events = events_service.get_recent_items(5)
        # Convert events to a list of dictionaries for JSON serialization
        event_dicts = [event.model_dump() for event in events]
        return jsonify(event_dicts), 200
    except Exception as e:
        log.exception(e)
        return jsonify({"status": "error", "message": "Failed to retrieve events"}), 500


@events_app.route('/log', methods=['POST'])
def log_event():
    json_data = request.json
    try:
        if json_data:
            current_timestamp = datetime.now()
            tags = json_data['tags']
            if tags:
                json_data["tags"] = [t.strip() for t in tags.split(',')]
            else:
                json_data["tags"] = []
            json_data["timestamp"] = int(current_timestamp.timestamp())
            event: Event = Event(**json_data)
            events_service.create(event)

            return jsonify({
                "status": "success",
                "message": ""
            })
    except Exception as e:
        log.exception(e)

    return jsonify({
        "status": "error",
        "message": "Nothing to log"
    }), 200


@events_app.route('/home')
def home():
    return render_template('events_home.html')
