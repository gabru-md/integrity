from enum import Enum
from functools import wraps
from typing import Optional, Dict, Any

from flask import abort, g, redirect, request, session

class Role(str, Enum):
    ADMIN = "admin"
    USER = "user"
    GUEST = "guest"


class PermissionManager:
    @staticmethod
    def get_current_role() -> Role:
        if not PermissionManager.is_authenticated():
            return Role.GUEST
        return Role.ADMIN if PermissionManager.is_admin() else Role.USER

    @staticmethod
    def is_authenticated() -> bool:
        return bool(session.get("user_id"))

    @staticmethod
    def is_admin() -> bool:
        return bool(session.get("is_admin"))

    @staticmethod
    def get_current_user_id() -> Optional[int]:
        return session.get("user_id")

    @staticmethod
    def get_current_user() -> Optional[Dict[str, Any]]:
        user_id = PermissionManager.get_current_user_id()
        if not user_id:
            return None

        return {
            "id": user_id,
            "username": session.get("username", ""),
            "display_name": session.get("display_name", ""),
            "is_admin": PermissionManager.is_admin(),
        }

    @staticmethod
    def login(user):
        session["user_id"] = user.id
        session["username"] = user.username
        session["display_name"] = user.display_name
        session["is_admin"] = user.is_admin

    @staticmethod
    def logout():
        session.pop("user_id", None)
        session.pop("username", None)
        session.pop("display_name", None)
        session.pop("is_admin", None)

    @staticmethod
    def can_write() -> bool:
        return PermissionManager.is_authenticated()

    @staticmethod
    def can_access_admin_panel() -> bool:
        return PermissionManager.is_admin()

    @staticmethod
    def can_view_app(app_name: str) -> bool:
        """ 
        Checks if the user has permission to view the app's base UI.
        Apps like 'users' are viewable but restricted by route-level logic.
        """
        if not PermissionManager.is_authenticated():
            return False

        # Admin-only structural apps
        admin_apps = {"devices", "processes", "heimdall", "apps"}
        safe_app_name = (app_name or "").lower()
        if safe_app_name in admin_apps:
            return PermissionManager.is_admin()
        return True

    @staticmethod
    def can_access_route(app_name: str, path: str) -> bool:
        """
        Refined Gabru Framework permission check.
        Decides if the current user can access a specific route within an app.
        """
        if not PermissionManager.is_authenticated():
            return False

        is_admin = PermissionManager.is_admin()
        safe_app_name = (app_name or "").lower()
        path = path.rstrip('/') or '/'

        # Users App Logic: Everyone can see profile, only admins can manage others
        if safe_app_name == "users":
            if "/profile" in path:
                return True
            return is_admin

        # Fallback to can_view_app for general apps
        return PermissionManager.can_view_app(app_name)

    @staticmethod
    def can_access_record(record) -> bool:
        if record is None:
            return False

        record_user_id = getattr(record, "user_id", None)
        if record_user_id is None:
            return PermissionManager.is_admin()
        return record_user_id == PermissionManager.get_current_user_id()

def requires_role(required_roles):
    if not isinstance(required_roles, list):
        required_roles = [required_roles]

    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            current = PermissionManager.get_current_role()
            if current not in required_roles:
                return abort(403)
            return f(*args, **kwargs)
        return decorated_function
    return decorator

def admin_required(f):
    return requires_role([Role.ADMIN])(f)

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not PermissionManager.is_authenticated():
            if request.method == "GET":
                next_path = request.full_path if request.query_string else request.path
                return redirect(f"/login?next={next_path}")
            return abort(401, description="Login required")
        return f(*args, **kwargs)
    return decorated_function

def write_access_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not PermissionManager.can_write():
            if not PermissionManager.is_authenticated():
                return abort(401, description="Login required")
            return abort(403, description="Write access required")
        return f(*args, **kwargs)
    return decorated_function
