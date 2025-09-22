from gabru.app import App
from model.event import Event
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


events_app = App('Events', EventService(), Event, _process_data_func=process_data)
