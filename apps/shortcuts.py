from datetime import datetime
from uuid import uuid4

from flask import jsonify, redirect

from gabru.flask.app import App
from model.event import Event
from services.events import EventService
from services.shortcuts import ShortcutService
from model.shortcut import Shortcut
import os
from dotenv import load_dotenv

from util.signer import sign_file_on_macbook

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
    json_data['signed'] = False

    return json_data


shortcuts_app = App('Shortcuts', ShortcutService(), Shortcut, _process_model_data_func=process_data,
                    get_recent_limit=10, home_template="shortcuts.html")

event_service = EventService()


@shortcuts_app.blueprint.route('/sign/<int:entity_id>', methods=['GET'])
def sign_shortcut(entity_id):
    shortcut: Shortcut = shortcuts_app.service.get_by_id(entity_id)
    if shortcut:
        filename = shortcut.filename
        signed_filename = f"signed_{filename}"

        shortcut_filepath = os.path.join(SERVER_FILES_FOLDER, filename)
        signed_shortcut_filepath = os.path.join(SERVER_FILES_FOLDER, signed_filename)

        if sign_file_on_macbook(shortcut_filepath, signed_shortcut_filepath):
            shortcut.filename = signed_filename
            shortcut.signed = True

            if shortcuts_app.service.update(shortcut):
                return redirect('shortcuts/home'), 302

    return jsonify({"error": f"Failed to sign shortcut"}), 500


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
