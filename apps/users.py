from apps.user_docs import build_app_user_guidance
from gabru.flask.app import App
from model.user import User
from services.users import UserService


def process_user_data(data):
    data["username"] = (data.get("username") or "").strip().lower()
    data["display_name"] = (data.get("display_name") or data.get("username") or "").strip()
    if not data.get("password"):
        data["password"] = None
    
    # Users created through the Admin Users App are automatically approved
    if "is_approved" not in data:
        data["is_approved"] = True
        
    return data


users_app = App(
    "Users",
    service=UserService(),
    model_class=User,
    _process_model_data_func=process_user_data,
    widget_enabled=False,
    user_guidance=build_app_user_guidance("Users"),
)
