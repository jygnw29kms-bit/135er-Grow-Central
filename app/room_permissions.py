"""Room-scoped capabilities. Never reuse the appliance service token as a user role.

An invited user has rights only in explicitly assigned rooms. Role names are
presentation labels; authorization always checks individual capabilities.
"""
from __future__ import annotations

from typing import Literal

Role = Literal["owner", "admin", "grower", "observer"]
PERMISSIONS: dict[str, frozenset[str]] = {
    "owner": frozenset({
        "room.view", "journal.view", "journal.write", "plant.write", "devices.view",
        "devices.control", "devices.assign", "automation.view", "automation.edit",
        "automation.activate", "alerts.view", "alerts.manage", "members.invite",
        "members.manage", "room.edit", "room.delete", "data.export", "camera.view",
    }),
    "admin": frozenset({
        "room.view", "journal.view", "journal.write", "plant.write", "devices.view",
        "devices.control", "devices.assign", "automation.view", "automation.edit",
        "automation.activate", "alerts.view", "alerts.manage", "members.invite",
        "room.edit", "data.export", "camera.view",
    }),
    "grower": frozenset({
        "room.view", "journal.view", "journal.write", "plant.write", "devices.view",
        "automation.view", "alerts.view", "camera.view",
    }),
    "observer": frozenset({
        "room.view", "journal.view", "devices.view", "automation.view",
        "alerts.view", "camera.view",
    }),
}
# Even admin cannot transfer ownership. Physical control is not given to growers
# by default, and privilege escalation is impossible through a custom role list.
ASSIGNABLE = frozenset({"admin", "grower", "observer"})


def allowed(role: str, permission: str) -> bool:
    return permission in PERMISSIONS.get(role, frozenset())


def assignable(by_role: str, requested_role: str) -> bool:
    if requested_role not in ASSIGNABLE:
        return False
    return by_role == "owner" or (
        by_role == "admin" and requested_role in {"grower", "observer"}
    )


def permission_matrix() -> dict[str, list[str]]:
    return {name: sorted(permissions) for name, permissions in PERMISSIONS.items()}
