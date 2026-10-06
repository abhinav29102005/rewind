"""Role-based access control (RBAC) permission matrix and decorators."""

from __future__ import annotations

import functools
from collections.abc import Callable
from typing import Any

from .models import Role, User


class PermissionDenied(Exception):  # noqa: N818
    """Raised when an actor lacks the required permission."""


# Permission matrix per Section 9.2
PERMISSIONS: dict[str, set[Role]] = {
    "view": {Role.ADMIN, Role.APPROVER, Role.VIEWER},
    "approve": {Role.ADMIN, Role.APPROVER},
    "session": {Role.ADMIN, Role.APPROVER},
    "rollback": {Role.ADMIN, Role.APPROVER},
    "policy": {Role.ADMIN},
    "manage_users": {Role.ADMIN},
    "relax_policy": {Role.ADMIN},
}


def has_permission(role: Role | str, permission: str) -> bool:
    r = Role(role) if isinstance(role, str) else role
    allowed_roles = PERMISSIONS.get(permission)
    if allowed_roles is None:
        raise ValueError(f"Unknown permission: {permission}")
    return r in allowed_roles


def check_permission(user: User | None, permission: str) -> None:
    if user is None:
        raise PermissionDenied("Authentication required")
    if not user.active:
        raise PermissionDenied("User account is inactive")
    if not has_permission(user.role, permission):
        raise PermissionDenied(f"Role {user.role.value!r} does not have permission {permission!r}")


def requires(permission: str) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
    """Decorator to enforce permissions on functions taking user as an argument."""
    def decorator(fn: Callable[..., Any]) -> Callable[..., Any]:
        @functools.wraps(fn)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            user = kwargs.get("current_user") or (args[0] if args and isinstance(args[0], User) else None)
            check_permission(user, permission)
            return fn(*args, **kwargs)
        return wrapper
    return decorator
