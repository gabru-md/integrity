from datetime import datetime
from uuid import uuid4

from flask import jsonify

from gabru.flask.app import App
from model.event import Event
from services.events import EventService
from services.shortcuts import ShortcutService
from model.shortcut import Shortcut
from gabru.apple.shortcuts import ShortcutBuilder
import os
from dotenv import load_dotenv
import json

load_dotenv()

RASBHARI_LOCAL_URL = os.getenv("RASBHARI_LOCAL_URL", "rasbhari.local:5000")
SERVER_FILES_FOLDER = os.getenv("SERVER_FILES_FOLDER", "/tmp")


def process_data(json_data):
    # update call
    if 'filename' in json_data:
        return json_data

    name = json_data['name']
    file_name = f"{'-'.join(f.lower() for f in name.split())}_{uuid4()}.shortcut"
    json_data['filename'] = file_name

    return json_data


shortcuts_app = App('Shortcuts', ShortcutService(), Shortcut, _process_model_data_func=process_data,
                    get_recent_limit=10)

event_service = EventService()


@shortcuts_app.blueprint.route('/invoke/<int:entity_id>', methods=['POST'])
def invoke_event_shortcut(entity_id):
    shortcut: Shortcut = shortcuts_app.service.get_by_id(entity_id)
    if shortcut:
        event_data = {
            "event_type": shortcut.event_type,
            "tags": ['shortcut-invoked'],
            "description": shortcut.description,
            "timestamp": int(datetime.now().timestamp())
        }

        event_service.create(Event(**event_data))
        return jsonify({"message": f"{shortcut.event_type} created successfully"}), 200
    return jsonify({"error": f"Failed to invoke shortcut event"}), 500
