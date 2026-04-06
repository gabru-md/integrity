from datetime import datetime

from flask import request, redirect, url_for, flash, session, jsonify
from apps.user_docs import build_app_user_guidance
from gabru.auth import PermissionManager
from gabru.flask.app import App
from gabru.flask.util import render_flask_template
from model.user import User
from processes.backup_scheduler import BackupScheduler
from services.eventing import emit_event_safely
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
users_app.register_process(BackupScheduler, enabled=True)


@users_app.blueprint.route("/profile", methods=["GET"])
def profile():
    user_id = PermissionManager.get_current_user_id()
    if not user_id:
        return redirect(url_for("login"))
    
    user = users_app.service.get_by_id(user_id)
    if not user:
        flash("User not found.", "error")
        return redirect(url_for("home"))
    
    return render_flask_template("profile.html", user=user)


@users_app.blueprint.route("/profile/update", methods=["POST"])
def update_profile():
    user_id = PermissionManager.get_current_user_id()
    if not user_id:
        return redirect(url_for("login"))
    
    user = users_app.service.get_by_id(user_id)
    if not user:
        flash("User not found.", "error")
        return redirect(url_for("home"))
    
    display_name = request.form.get("display_name")
    ntfy_topic = request.form.get("ntfy_topic")
    experience_mode = request.form.get("experience_mode")
    recommendations_enabled = request.form.get("recommendations_enabled") == "on"
    recommendation_limit_raw = request.form.get("recommendation_limit", "").strip()
    password = request.form.get("password")
    confirm_password = request.form.get("confirm_password")
    
    if password and password != confirm_password:
        flash("Passwords do not match.", "error")
        return redirect(url_for("Users.profile"))
    
    # Update user object
    user.display_name = display_name
    user.ntfy_topic = ntfy_topic
    user.experience_mode = users_app.service.normalize_experience_mode(experience_mode)
    user.recommendations_enabled = recommendations_enabled
    try:
        user.recommendation_limit = max(0, int(recommendation_limit_raw))
    except ValueError:
        user.recommendation_limit = max(0, int(user.recommendation_limit if user.recommendation_limit is not None else 2))
    if password:
        user.password = password
    
    success = users_app.service.update(user)
    if success:
        flash("Profile updated successfully!", "success")
        session["display_name"] = user.display_name
        session["experience_mode"] = user.experience_mode
    else:
        flash("Failed to update profile.", "error")
        
    return redirect(url_for("Users.profile"))


@users_app.blueprint.route("/profile/api-key/regenerate", methods=["POST"])
def regenerate_api_key():
    user_id = PermissionManager.get_current_user_id()
    if not user_id:
        return redirect(url_for("login"))

    user = users_app.service.get_by_id(user_id)
    if not user:
        flash("User not found.", "error")
        return redirect(url_for("home"))

    new_api_key = users_app.service.regenerate_api_key(user_id)
    if not new_api_key:
        flash("Failed to regenerate API key.", "error")
        return redirect(url_for("Users.profile"))

    emit_event_safely(
        users_app.log,
        event_type="user:api_key_regenerated",
        timestamp=datetime.now(),
        description=f"API key regenerated for {user.username}",
        tags=["security", "user"],
    )

    flash("API key regenerated successfully.", "success")
    return redirect(url_for("Users.profile"))


@users_app.blueprint.route("/profile/onboarding", methods=["POST"])
def update_onboarding():
    user_id = PermissionManager.get_current_user_id()
    if not user_id:
        if request.is_json:
            return jsonify({"error": "Login required"}), 401
        return redirect(url_for("login"))

    user = users_app.service.get_by_id(user_id)
    if not user:
        if request.is_json:
            return jsonify({"error": "User not found"}), 404
        flash("User not found.", "error")
        return redirect(url_for("home"))

    data = request.get_json(silent=True) if request.is_json else request.form
    completed_value = data.get("completed")
    if isinstance(completed_value, str):
        completed = completed_value.strip().lower() in {"1", "true", "yes", "on"}
    else:
        completed = bool(completed_value)

    user.onboarding_completed = completed
    success = users_app.service.update(user)
    if success:
        session["onboarding_completed"] = completed
        if request.is_json:
            return jsonify({"ok": True, "onboarding_completed": completed}), 200
        flash("Tutorial state updated.", "success")
    else:
        if request.is_json:
            return jsonify({"error": "Failed to update tutorial state"}), 500
        flash("Failed to update tutorial state.", "error")

    return redirect(url_for("Users.profile"))
