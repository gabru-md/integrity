from enum import Enum
from functools import wraps
from flask import session, request, abort, g

class Role(str, Enum):
    ADMIN = "admin"
    USER = "user"
    GUEST = "guest"

class PermissionManager:
    @staticmethod
    def get_current_role() -> Role:
        # Default to ADMIN for now if not set, or we can make it configurable
        # checking session for role
        role_str = session.get('role', Role.ADMIN.value)
        try:
            return Role(role_str)
        except ValueError:
            return Role.GUEST

    @staticmethod
    def set_role(role: Role):
        session['role'] = role.value

    @staticmethod
    def can_write() -> bool:
        return PermissionManager.get_current_role() == Role.ADMIN

    @staticmethod
    def can_access_admin_panel() -> bool:
        return PermissionManager.get_current_role() == Role.ADMIN

    @staticmethod
    def can_view_app(app_name: str) -> bool:
        role = PermissionManager.get_current_role()
        
        # Admin sees everything
        if role == Role.ADMIN:
            return True
            
        # Guest only sees Blogs
        if role == Role.GUEST:
            return app_name.lower() == 'blogs'
            
        # User sees standard apps but not admin/system apps
        if role == Role.USER:
            # List of admin-only apps/features
            admin_apps = ['devices', 'processes', 'heimdall', 'apps']
            return app_name.lower() not in admin_apps
            
        return False

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

def write_access_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not PermissionManager.can_write():
            return abort(403, description="Write access required")
        return f(*args, **kwargs)
    return decorated_function
