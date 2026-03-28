from gabru.flask.app import App
from apps.user_docs import build_app_user_guidance
from model.event import Event
from processes.courier.courier import Courier
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


events_app = App('Events', EventService(), Event, _process_model_data_func=process_data, get_recent_limit=15,
                 widget_type="timeline", user_guidance=build_app_user_guidance("Events"))

# Courier enabled to handle notifications (Default: ntfy.sh, Tag: 'email' for SendGrid)
events_app.register_process(Courier, enabled=True)
