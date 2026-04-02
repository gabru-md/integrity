from enum import Enum
from functools import wraps
from typing import Optional, Dict, Any

from flask import abort, g, redirect, request, session

from gabru.contracts import AuthProvider

class Role(str, Enum):
    ADMIN = "admin"
    USER = "user"
    GUEST = "guest"


class PermissionManager:
    _auth_provider: Optional[AuthProvider] = None

    @staticmethod
    def configure(auth_provider: AuthProvider):
        PermissionManager._auth_provider = auth_provider

    @staticmethod
    def _get_request_api_key() -> str:
        direct_header = request.headers.get("X-API-Key", "").strip()
        if direct_header:
            return direct_header
        authorization = request.headers.get("Authorization", "").strip()
        if authorization.lower().startswith("apikey "):
            return authorization[7:].strip()
        return ""

    @staticmethod
    def _get_request_authenticated_user():
        if getattr(g, "_authenticated_user_resolved", False):
            return getattr(g, "_authenticated_user", None)

        if session.get("user_id"):
            user = {
                "id": session.get("user_id"),
                "username": session.get("username", ""),
                "display_name": session.get("display_name", ""),
                "is_admin": bool(session.get("is_admin")),
                "onboarding_completed": bool(session.get("onboarding_completed")),
                "auth_type": "session",
            }
            g._authenticated_user = user
            g._authenticated_user_resolved = True
            return user

        api_key = PermissionManager._get_request_api_key()
        if not api_key:
            g._authenticated_user = None
            g._authenticated_user_resolved = True
            return None

        if PermissionManager._auth_provider is None:
            raise RuntimeError("PermissionManager auth provider is not configured")

        user = PermissionManager._auth_provider.authenticate_api_key(api_key)
        if not user:
            g._authenticated_user = None
            g._authenticated_user_resolved = True
            return None

        g._authenticated_user = {
            "id": user.id,
            "username": user.username,
            "display_name": user.display_name,
            "is_admin": user.is_admin,
            "api_key": user.api_key,
            "onboarding_completed": getattr(user, "onboarding_completed", False),
            "auth_type": "api_key",
        }
        g._authenticated_user_resolved = True
        return g._authenticated_user

    @staticmethod
    def get_current_role() -> Role:
        if not PermissionManager.is_authenticated():
            return Role.GUEST
        return Role.ADMIN if PermissionManager.is_admin() else Role.USER

    @staticmethod
    def is_authenticated() -> bool:
        return PermissionManager._get_request_authenticated_user() is not None

    @staticmethod
    def is_admin() -> bool:
        user = PermissionManager._get_request_authenticated_user()
        return bool(user and user.get("is_admin"))

    @staticmethod
    def get_current_user_id() -> Optional[int]:
        user = PermissionManager._get_request_authenticated_user()
        return user.get("id") if user else None

    @staticmethod
    def get_current_user() -> Optional[Dict[str, Any]]:
        user = PermissionManager._get_request_authenticated_user()
        if not user:
            return None

        return {
            "id": user.get("id"),
            "username": user.get("username", ""),
            "display_name": user.get("display_name", ""),
            "is_admin": bool(user.get("is_admin")),
            "onboarding_completed": bool(user.get("onboarding_completed")),
            "auth_type": user.get("auth_type", "session"),
        }

    @staticmethod
    def login(user):
        session["user_id"] = user.id
        session["username"] = user.username
        session["display_name"] = user.display_name
        session["is_admin"] = user.is_admin
        session["onboarding_completed"] = getattr(user, "onboarding_completed", False)
        g._authenticated_user = {
            "id": user.id,
            "username": user.username,
            "display_name": user.display_name,
            "is_admin": user.is_admin,
            "api_key": getattr(user, "api_key", None),
            "onboarding_completed": getattr(user, "onboarding_completed", False),
            "auth_type": "session",
        }
        g._authenticated_user_resolved = True

    @staticmethod
    def logout():
        session.pop("user_id", None)
        session.pop("username", None)
        session.pop("display_name", None)
        session.pop("is_admin", None)
        session.pop("onboarding_completed", None)
        g._authenticated_user = None
        g._authenticated_user_resolved = True

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
