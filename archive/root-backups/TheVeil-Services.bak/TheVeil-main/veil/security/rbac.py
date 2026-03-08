"""
RBAC - The Veil Role-Based Access Control
=========================================
P1 Security Organ: "Each role has its purpose and boundary."

Provides:
- Role definitions and hierarchy
- Permission checking
- Route protection decorators
- Resource-level access control
"""

from __future__ import annotations

from functools import wraps
from typing import Optional, List, Callable, Any, Union

from .models import Role, Permission, ROLE_PERMISSIONS, User, Session


class RBAC:
    """
    Role-Based Access Control for The Veil.
    
    Manages permissions based on user roles and provides
    decorators for protecting routes and functions.
    """
    
    # Role hierarchy (higher index = more privileges)
    ROLE_HIERARCHY = [Role.VIEWER, Role.OPERATOR, Role.ADMIN, Role.SYSTEM]
    
    @staticmethod
    def get_permissions(role: Role) -> List[Permission]:
        """Get all permissions for a role."""
        return ROLE_PERMISSIONS.get(role, [])
    
    @staticmethod
    def has_permission(user: Union[User, Session], permission: Permission) -> bool:
        """Check if a user or session has a specific permission."""
        role = user.role if isinstance(user, (User, Session)) else None
        if role is None:
            return False
        return permission in ROLE_PERMISSIONS.get(role, [])
    
    @staticmethod
    def has_role(user: Union[User, Session], required_role: Role) -> bool:
        """
        Check if user has at least the required role level.
        Uses role hierarchy for comparison.
        """
        user_role = user.role if isinstance(user, (User, Session)) else None
        if user_role is None:
            return False
        
        try:
            user_level = RBAC.ROLE_HIERARCHY.index(user_role)
            required_level = RBAC.ROLE_HIERARCHY.index(required_role)
            return user_level >= required_level
        except ValueError:
            return False
    
    @staticmethod
    def has_any_permission(user: Union[User, Session], permissions: List[Permission]) -> bool:
        """Check if user has any of the specified permissions."""
        return any(RBAC.has_permission(user, p) for p in permissions)
    
    @staticmethod
    def has_all_permissions(user: Union[User, Session], permissions: List[Permission]) -> bool:
        """Check if user has all of the specified permissions."""
        return all(RBAC.has_permission(user, p) for p in permissions)
    
    @staticmethod
    def can_manage_user(manager: Union[User, Session], target: User) -> bool:
        """Check if manager can modify target user."""
        # Can't modify yourself (except password)
        if isinstance(manager, User) and manager.id == target.id:
            return False
        if isinstance(manager, Session) and manager.user_id == target.id:
            return False
        
        # Must have MANAGE_USERS permission
        if not RBAC.has_permission(manager, Permission.MANAGE_USERS):
            return False
        
        # Can only manage users of lower role level
        manager_role = manager.role
        try:
            manager_level = RBAC.ROLE_HIERARCHY.index(manager_role)
            target_level = RBAC.ROLE_HIERARCHY.index(target.role)
            return manager_level > target_level
        except ValueError:
            return False
    
    @staticmethod
    def can_assign_role(assigner: Union[User, Session], role: Role) -> bool:
        """Check if user can assign a specific role."""
        if not RBAC.has_permission(assigner, Permission.MANAGE_ROLES):
            return False
        
        # Can only assign roles lower than own
        assigner_role = assigner.role
        try:
            assigner_level = RBAC.ROLE_HIERARCHY.index(assigner_role)
            role_level = RBAC.ROLE_HIERARCHY.index(role)
            return assigner_level > role_level
        except ValueError:
            return False


# ============================================================================
# Decorators for Route Protection
# ============================================================================

class AuthorizationError(Exception):
    """Raised when authorization fails."""
    def __init__(self, message: str, required: str = None):
        self.message = message
        self.required = required
        super().__init__(message)


def require_permission(*permissions: Permission):
    """
    Decorator to require specific permission(s) for a function.
    
    Usage:
        @require_permission(Permission.VIEW_ORGANS)
        def get_organs(user: User):
            ...
    
    The decorated function must receive a 'user' or 'session' argument.
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            # Try to find user/session in kwargs
            user = kwargs.get('user') or kwargs.get('session') or kwargs.get('current_user')
            
            # Try to find in args (assume first arg if User/Session type)
            if user is None and args:
                for arg in args:
                    if isinstance(arg, (User, Session)):
                        user = arg
                        break
            
            if user is None:
                raise AuthorizationError("No user context provided")
            
            # Check permissions (require ANY of the specified permissions)
            if not RBAC.has_any_permission(user, list(permissions)):
                perm_names = ", ".join(p.value for p in permissions)
                raise AuthorizationError(
                    f"Permission denied. Required: {perm_names}",
                    required=perm_names
                )
            
            return func(*args, **kwargs)
        
        # Store required permissions for introspection
        wrapper._required_permissions = permissions
        return wrapper
    
    return decorator


def require_role(role: Role):
    """
    Decorator to require a minimum role level for a function.
    
    Usage:
        @require_role(Role.ADMIN)
        def admin_only_function(user: User):
            ...
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            user = kwargs.get('user') or kwargs.get('session') or kwargs.get('current_user')
            
            if user is None and args:
                for arg in args:
                    if isinstance(arg, (User, Session)):
                        user = arg
                        break
            
            if user is None:
                raise AuthorizationError("No user context provided")
            
            if not RBAC.has_role(user, role):
                raise AuthorizationError(
                    f"Permission denied. Required role: {role.value}",
                    required=role.value
                )
            
            return func(*args, **kwargs)
        
        wrapper._required_role = role
        return wrapper
    
    return decorator


def require_all_permissions(*permissions: Permission):
    """
    Decorator to require ALL specified permissions.
    
    Usage:
        @require_all_permissions(Permission.VIEW_ORGANS, Permission.RESTART_ORGAN)
        def restart_organ(user: User, organ_name: str):
            ...
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            user = kwargs.get('user') or kwargs.get('session') or kwargs.get('current_user')
            
            if user is None and args:
                for arg in args:
                    if isinstance(arg, (User, Session)):
                        user = arg
                        break
            
            if user is None:
                raise AuthorizationError("No user context provided")
            
            if not RBAC.has_all_permissions(user, list(permissions)):
                perm_names = ", ".join(p.value for p in permissions)
                raise AuthorizationError(
                    f"Permission denied. Required all: {perm_names}",
                    required=perm_names
                )
            
            return func(*args, **kwargs)
        
        wrapper._required_permissions = permissions
        wrapper._require_all = True
        return wrapper
    
    return decorator


# ============================================================================
# FastAPI Integration Helpers
# ============================================================================

def get_route_permissions(route_path: str, method: str = "GET") -> List[Permission]:
    """
    Get required permissions for a route based on path patterns.
    This provides a centralized permission mapping.
    """
    # Normalize path
    path = route_path.lower().rstrip('/')
    method = method.upper()
    
    # Define route -> permission mappings
    ROUTE_PERMISSIONS = {
        # Dashboard
        ("GET", "/"): [Permission.VIEW_DASHBOARD],
        ("GET", "/status"): [Permission.VIEW_STATUS],
        
        # Patients
        ("GET", "/patients"): [Permission.VIEW_PATIENTS],
        ("POST", "/patients"): [Permission.CREATE_PATIENT],
        ("GET", "/patients/*"): [Permission.VIEW_PATIENTS],
        ("PUT", "/patients/*"): [Permission.UPDATE_PATIENT],
        ("DELETE", "/patients/*"): [Permission.DELETE_PATIENT],
        ("GET", "/discharged"): [Permission.VIEW_PATIENTS],
        
        # Organs
        ("GET", "/organs"): [Permission.VIEW_ORGANS],
        ("GET", "/api/organs"): [Permission.VIEW_ORGANS],
        ("POST", "/api/organs/*/start"): [Permission.START_ORGAN],
        ("POST", "/api/organs/*/stop"): [Permission.STOP_ORGAN],
        ("POST", "/api/organs/*/restart"): [Permission.RESTART_ORGAN],
        
        # System
        ("POST", "/api/restart"): [Permission.SYSTEM_RESTART],
        ("GET", "/api/systems"): [Permission.VIEW_STATUS],
        
        # Audit
        ("GET", "/audit"): [Permission.VIEW_AUDIT],
        ("GET", "/api/audit"): [Permission.VIEW_AUDIT],
        
        # Security
        ("GET", "/security"): [Permission.VIEW_SECURITY],
        ("GET", "/api/sessions"): [Permission.MANAGE_SESSIONS],
        
        # User Management
        ("GET", "/users"): [Permission.MANAGE_USERS],
        ("POST", "/users"): [Permission.MANAGE_USERS],
        ("PUT", "/users/*"): [Permission.MANAGE_USERS],
        ("DELETE", "/users/*"): [Permission.MANAGE_USERS],
    }
    
    # Exact match first
    key = (method, path)
    if key in ROUTE_PERMISSIONS:
        return ROUTE_PERMISSIONS[key]
    
    # Wildcard match
    for (route_method, route_pattern), perms in ROUTE_PERMISSIONS.items():
        if route_method != method:
            continue
        
        if '*' in route_pattern:
            # Convert pattern to regex-like matching
            pattern_parts = route_pattern.split('/')
            path_parts = path.split('/')
            
            if len(pattern_parts) != len(path_parts):
                continue
            
            match = True
            for pp, pathp in zip(pattern_parts, path_parts):
                if pp != '*' and pp != pathp:
                    match = False
                    break
            
            if match:
                return perms
    
    # Default: require dashboard view for unknown routes
    return [Permission.VIEW_DASHBOARD]


# ============================================================================
# Public Routes (no auth required)
# ============================================================================

PUBLIC_ROUTES = {
    "/login",
    "/api/auth/login",
    "/api/auth/refresh",
    "/static",
    "/favicon.ico",
    "/health",
    "/api/health",
}


def is_public_route(path: str) -> bool:
    """Check if a route is public (no auth required)."""
    path = path.lower().rstrip('/')
    
    for public in PUBLIC_ROUTES:
        if path == public or path.startswith(public + '/'):
            return True
    
    return False
