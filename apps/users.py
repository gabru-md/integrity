from flask import render_template, request, redirect, url_for, flash, session
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


@users_app.blueprint.route("/profile", methods=["GET"])
def profile():
    user_id = session.get("user_id")
    if not user_id:
        return redirect(url_for("login"))
    
    user = users_app.service.get_by_id(user_id)
    if not user:
        flash("User not found.", "error")
        return redirect(url_for("home"))
    
    return render_template("profile.html", user=user)


@users_app.blueprint.route("/profile/update", methods=["POST"])
def update_profile():
    user_id = session.get("user_id")
    if not user_id:
        return redirect(url_for("login"))
    
    user = users_app.service.get_by_id(user_id)
    if not user:
        flash("User not found.", "error")
        return redirect(url_for("home"))
    
    display_name = request.form.get("display_name")
    ntfy_topic = request.form.get("ntfy_topic")
    password = request.form.get("password")
    confirm_password = request.form.get("confirm_password")
    
    if password and password != confirm_password:
        flash("Passwords do not match.", "error")
        return redirect(url_for("Users.profile"))
    
    # Update user object
    user.display_name = display_name
    user.ntfy_topic = ntfy_topic
    if password:
        user.password = password
    
    success = users_app.service.update(user)
    if success:
        flash("Profile updated successfully!", "success")
        # Update session display name if it's stored there
        session["display_name"] = user.display_name
    else:
        flash("Failed to update profile.", "error")
        
    return redirect(url_for("Users.profile"))
