from uuid import uuid4

from gabru.flask.app import App
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

    event_type = json_data['event_type']
    name = json_data['name']
    description = json_data['description']

    file_name = f"{'-'.join(f.lower() for f in name.split())}_{uuid4()}.shortcut"

    filepath = os.path.join(SERVER_FILES_FOLDER, file_name)

    builder = ShortcutBuilder(name)

    # Create JSON as text first
    json_text = json.dumps({
        "event_type": event_type,
        "tags": ['shortcut-invoked'],
        "description": description
    })
    builder.add_text(json_text)


    builder.add_post_request(
        url=RASBHARI_LOCAL_URL + "/events/",
        headers={"Content-Type": "application/json"}
        # Don't provide body or json_body - it will use the previous text action's output
    )

    saved_file_path = builder.save(filepath=filepath)

    if saved_file_path:
        json_data['filename'] = file_name

    return json_data


shortcuts_app = App('Shortcuts', ShortcutService(), Shortcut, _process_model_data_func=process_data,
                    get_recent_limit=10)
