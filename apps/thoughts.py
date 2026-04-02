from datetime import datetime

from apps.user_docs import build_app_user_guidance
from gabru.flask.app import App
from model.thought import Thought
from services.thoughts import ThoughtService


def process_data(json_data):
    json_data["created_at"] = datetime.now()
    return json_data


thoughts_app = App('Thoughts', ThoughtService(), Thought, _process_model_data_func=process_data, get_recent_limit=20,
                   home_template="thoughts.html",
                   widget_type="timeline", widget_recent_limit=3,
                   user_guidance=build_app_user_guidance("Thoughts"))
