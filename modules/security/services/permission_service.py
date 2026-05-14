from __future__ import annotations


ROLE_PERMISSIONS = {
    "admin": {
        "detection.run",
        "detection.view_result",
        "face.identify",
        "profile.view",
        "profile.view_sensitive",
        "graph.view",
        "graph.run_algo",
        "dispatch.send",
        "dispatch.sms",
        "training.manage",
        "security.audit_view",
    },
    "analyst": {
        "detection.run",
        "detection.view_result",
        "face.identify",
        "profile.view",
        "graph.view",
        "graph.run_algo",
        "training.manage",
    },
    "dispatcher": {
        "profile.view",
        "dispatch.send",
        "dispatch.sms",
    },
    "viewer": {
        "detection.view_result",
        "profile.view",
        "graph.view",
    },
}


def permissions_for_roles(roles: list[str]) -> list[str]:
    permissions: set[str] = set()
    for role in roles:
        permissions.update(ROLE_PERMISSIONS.get(role, set()))
    return sorted(permissions)


def has_permission(roles: list[str], permission: str) -> bool:
    return permission in permissions_for_roles(roles)

