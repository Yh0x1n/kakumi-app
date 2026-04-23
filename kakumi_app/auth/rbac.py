"""
Role-Based Access Control (RBAC) module for Kakumi Tournament Manager.
Defines permission matrix, decorators, and helper functions for authorization.
Integrates with AuthService and AuthState.
"""

from typing import List, Dict, Callable
from functools import wraps

import reflex as rx

from kakumi_app.services.auth_service import AuthService


# Permission constants
PERMISSIONS = {
    # Dashboard
    "VIEW_DASHBOARD": "view_dashboard",
    # Tournament Management
    "CREATE_TOURNAMENT": "create_tournament",
    "EDIT_TOURNAMENT": "edit_tournament",
    "DELETE_TOURNAMENT": "delete_tournament",
    "MANAGE_TOURNAMENT_STATUS": "manage_tournament_status",
    # Category Management
    "CREATE_CATEGORY": "create_category",
    "EDIT_CATEGORY": "edit_category",
    "DELETE_CATEGORY": "delete_category",
    # Match & Scoring
    "VIEW_MATCH": "view_match",
    "EDIT_MATCH_SCORE": "edit_match_score",
    "MANAGE_PENALTIES": "manage_penalties",
    "ADVANCE_WINNER": "advance_winner",
    # Referee Management
    "ASSIGN_REFEREE": "assign_referee",
    "MANAGE_REFEREE": "manage_referee",
    # Athlete & Team Management
    "MANAGE_ATHLETES": "manage_athletes",
    "MANAGE_TEAMS": "manage_teams",
    "IMPORT_DATA": "import_data",
    "EXPORT_DATA": "export_data",
    # User Management (Admin only)
    "MANAGE_USERS": "manage_users",
    "VIEW_USER_LIST": "view_user_list",
    # System
    "SYSTEM_SETTINGS": "system_settings",
    "VIEW_AUDIT_LOG": "view_audit_log",
}

# Permission matrix: role -> list of permission strings
PERMISSION_MATRIX: Dict[str, List[str]] = {
    "ADMIN": list(PERMISSIONS.values()),  # All permissions
    "OPERATOR": [
        PERMISSIONS["VIEW_DASHBOARD"],
        PERMISSIONS["CREATE_TOURNAMENT"],
        PERMISSIONS["EDIT_TOURNAMENT"],
        PERMISSIONS["MANAGE_TOURNAMENT_STATUS"],
        PERMISSIONS["CREATE_CATEGORY"],
        PERMISSIONS["EDIT_CATEGORY"],
        PERMISSIONS["VIEW_MATCH"],
        PERMISSIONS["EDIT_MATCH_SCORE"],
        PERMISSIONS["MANAGE_PENALTIES"],
        PERMISSIONS["ADVANCE_WINNER"],
        PERMISSIONS["ASSIGN_REFEREE"],
        PERMISSIONS["MANAGE_ATHLETES"],
        PERMISSIONS["MANAGE_TEAMS"],
        PERMISSIONS["IMPORT_DATA"],
        PERMISSIONS["EXPORT_DATA"],
        PERMISSIONS["VIEW_USER_LIST"],  # Can view but not manage users
    ],
    "VIEWER": [
        PERMISSIONS["VIEW_DASHBOARD"],
        PERMISSIONS["VIEW_MATCH"],
        # View-only access to tournament data (handled via UI, not explicit permissions)
    ],
}

def has_permission(user_role: str, permission: str) -> bool:
    """Check if a role has a specific permission."""
    allowed = PERMISSION_MATRIX.get(user_role, [])
    return permission in allowed


def get_role_permissions(role: str) -> List[str]:
    """Get all permissions for a given role."""
    return PERMISSION_MATRIX.get(role, []).copy()


def get_all_permissions() -> Dict[str, str]:
    """Return mapping of permission constant to permission string."""
    return PERMISSIONS.copy()


def require_permission(permission: str):
    """
    Decorator to enforce permission-based access control.
    Can be used on functions that receive a token or user_role as argument.
    Example usage:
        @require_permission("EDIT_MATCH_SCORE")
        def update_score(token: str, ...):
            ...
    """

    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            # Try to extract token from arguments
            token = kwargs.get("token") or (args[0] if args else None)
            if not token or not isinstance(token, str):
                raise PermissionError("Authentication token required")

            # Validate token and get user role
            payload = AuthService.validate_token(token)
            if not payload:
                raise PermissionError("Invalid or expired token")
            user_role = payload.get("role")
            if not user_role:
                raise PermissionError("Role not found in token")

            # Check permission
            if not has_permission(user_role, permission):
                raise PermissionError(f"Permission denied: {permission}")

            return func(*args, **kwargs)

        return wrapper

    return decorator
# Integration with AuthState: extend AuthState with RBAC methods
class RBACMixin:
    """Mixin to add RBAC capabilities to AuthState (optional)."""

    def has_permission(self, permission: str) -> bool:
        """Check if current user has a specific permission."""
        if not self.is_authenticated:
            return False
        return has_permission(self.user_role, permission)

    def require_permission(self, permission: str) -> bool:
        """Check permission and raise if not allowed (for use in state methods)."""
        if not self.has_permission(permission):
            raise PermissionError(f"Permission denied: {permission}")
        return True


# Helper for UI components: check permission in frontend (returns bool)
def check_permission_state(auth_state: rx.State, permission: str) -> bool:
    """
    Helper to check permission from a state that has user_role attribute.
    Used in conditional rendering.
    """
    if not hasattr(auth_state, "user_role"):
        return False
    return has_permission(auth_state.user_role, permission)


# Export for convenience
__all__ = [
    "PERMISSIONS",
    "PERMISSION_MATRIX",
    "has_permission",
    "get_role_permissions",
    "get_all_permissions",
    "require_permission",
    "RBACMixin",
    "check_permission_state",
]
