# Users and RBAC

Roles:

- Administrator: full management access
- Operator: operate devices, manage schedules/automations, view history
- Viewer: read-only dashboard/sensor/history access
- Device/Agent: telemetry, heartbeat and authorized command processing

Core tables: `users`, `roles`, `permissions`, `user_roles`, `role_permissions`, `sessions`.

Authorization must be enforced by backend endpoints, not only hidden in the UI.
