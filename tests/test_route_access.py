"""Public/admin path matching and the permissions the RBAC middleware derives."""

from __future__ import annotations

import pytest

from app.api.middleware.base import path_matches
from app.api.middleware.rbac import RBACMiddleware
from config import Config

SETTINGS = Config().settings


@pytest.mark.parametrize(
    ("path", "expected"),
    [
        ("/", True),
        ("/api/v1/users", False),  # "/" must not make everything public
        ("/api/v1/auth/login", True),
        ("/api/v1/auth/login-admin", False),  # whole segments only
        ("/api/v1/auth/logout", False),
        ("/docs/oauth2-redirect", True),
        ("/docsx", False),
        ("/api/v1/oauth/google/callback", True),
        ("/api/v1/oauth/google/link", False),
    ],
)
def test_public_paths_match_whole_segments(path, expected):
    public = SETTINGS.public_paths
    assert path_matches(path, public) is expected


def test_templated_admin_paths_match_one_segment():
    assert path_matches("/users/42/role", ["/users/{id}/role"])
    assert not path_matches("/users/role", ["/users/{id}/role"])


def test_sensitive_surfaces_are_admin_only():
    admin_only = SETTINGS.admin_only_paths
    for path in ("/api/v1/rbac/roles", "/api/v1/metrics"):
        assert path_matches(path, admin_only), path


def permissions_of(role_id: str, roles: dict) -> set[str]:
    role = roles[role_id]
    inherited = set().union(*(permissions_of(r, roles) for r in role.get("inherits", [])))
    return set(role["permissions"]) | inherited


STAFF_ONLY = {"users:read", "users:write"}  # user administration: managers and admins
ADMIN_ONLY = {"users:delete"}  # held only through the "*" wildcard


def required_permissions(env) -> set[str]:
    """Permission the middleware demands for every non-public, non-admin-only route."""
    to_permission = RBACMiddleware._path_to_permission
    methods = {"get", "post", "put", "patch", "delete"}
    return {
        to_permission(path, method.upper())
        for path, operations in env.app.openapi()["paths"].items()
        if not path_matches(path, SETTINGS.public_paths)
        and not path_matches(path, SETTINGS.admin_only_paths)
        for method in operations
        if method in methods
    }


def test_every_authenticated_api_route_is_grantable_to_a_normal_user(env):
    """The middleware demands '<resource>:<action>' per path; the user role must hold it."""
    granted = permissions_of("user", SETTINGS.rbac_roles)

    missing = sorted(required_permissions(env) - granted - STAFF_ONLY - ADMIN_ONLY)

    assert not missing, f"user role lacks permissions the middleware requires: {missing}"


def test_staff_only_permissions_are_held_by_managers_but_not_users(env):
    roles = SETTINGS.rbac_roles
    assert STAFF_ONLY <= required_permissions(env)  # the carve-out is still needed
    assert STAFF_ONLY <= permissions_of("manager", roles)
    assert not STAFF_ONLY & permissions_of("user", roles)
