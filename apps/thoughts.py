from datetime import datetime

from gabru.flask.app import App
from model.thought import Thought
from services.thoughts import ThoughtService


def process_data(json_data):
    current_timestamp = datetime.now()
    json_data["created_at"] = int(current_timestamp.timestamp())
    return json_data


thoughts_app = App('Thoughts', ThoughtService(), Thought, _process_data_func=process_data, get_recent_limit=10)
