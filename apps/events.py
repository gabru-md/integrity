from gabru.flask.app import App
from model.event import Event
from processes.courier.courier import Courier
from processes.heimdall.heimdall import Heimdall
from services.events import EventService
from datetime import datetime


def process_data(json_data):
    current_timestamp = datetime.now()
    tags = json_data['tags']
    if tags:
        json_data["tags"] = [t.strip() for t in tags.split(',')]
    else:
        json_data["tags"] = []
    json_data["timestamp"] = int(current_timestamp.timestamp())
    return json_data


events_app = App('Events', EventService(), Event, _process_model_data_func=process_data, get_recent_limit=15)

# disabled until I figure a reporting mechanism otherwise emails exhaust
events_app.register_process(Courier, enabled=False)

# disabled until I set up the esp32cams
events_app.register_process(Heimdall, enabled=False)