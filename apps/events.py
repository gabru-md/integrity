from flask import request

from gabru.flask.app import App
from gabru.flask.util import render_flask_template
from apps.user_docs import build_app_user_guidance
from model.event import Event
from processes.courier.courier import Courier
from processes.session_inference_processor import SessionInferenceProcessor
from services.events import EventService
from datetime import datetime


RASBHARI_EVENT_PREFIXES = (
    "kanban:",
    "media:",
    "report:",
    "skill:",
    "project:",
    "blog:",
    "browser:",
    "local:",
    "agent:",
    "device:",
    "tracking:",
)
RASBHARI_EVENT_TYPES = {
}


def event_scope(event: Event) -> str:
    event_type = (event.event_type or "").strip().lower()
    if event_type in RASBHARI_EVENT_TYPES:
        return "rasbhari"
    if event_type.startswith(RASBHARI_EVENT_PREFIXES):
        return "rasbhari"
    return "user"


def process_data(json_data):
    current_timestamp = datetime.now()
    tags = json_data.get("tags")
    if isinstance(tags, list):
        json_data["tags"] = [str(tag).strip() for tag in tags if str(tag).strip()]
    elif isinstance(tags, str):
        json_data["tags"] = [tag.strip() for tag in tags.split(",") if tag.strip()]
    else:
        json_data["tags"] = []
    json_data["timestamp"] = current_timestamp
    return json_data


class EventsApp(App[Event]):
    def setup_home_route(self):
        @self.blueprint.route('/home')
        def home():
            scope = (request.args.get("scope") or "all").strip().lower()
            if scope not in {"all", "user", "rasbhari"}:
                scope = "all"
            limit = int(request.args.get("limit") or 80)
            limit = max(10, min(limit, 200))

            events = self.service.find_all(sort_by={"timestamp": "DESC"})
            decorated_events = []
            counts = {"all": 0, "user": 0, "rasbhari": 0}
            for event in events:
                current_scope = event_scope(event)
                counts["all"] += 1
                counts[current_scope] += 1
                if scope != "all" and current_scope != scope:
                    continue
                event_data = event.model_dump() if hasattr(event, "model_dump") else event.dict()
                event_data["scope"] = current_scope
                decorated_events.append(event_data)
                if len(decorated_events) >= limit:
                    break

            return render_flask_template(
                self.home_template,
                model_class_attributes=self.model_class_attributes,
                model_class_name=self.model_class.__name__,
                app_name=self.name,
                user_guidance=self.user_guidance,
                events=decorated_events,
                event_scope=scope,
                event_counts=counts,
                event_limit=limit,
            )


events_app = EventsApp('Events', EventService(), Event, _process_model_data_func=process_data, get_recent_limit=15,
                       home_template="events.html", widget_type="timeline", user_guidance=build_app_user_guidance("Events"))

# Courier enabled to handle notifications (Default: ntfy.sh, Tag: 'email' for SendGrid)
events_app.register_process(Courier, enabled=True)
events_app.register_process(SessionInferenceProcessor, enabled=True)
