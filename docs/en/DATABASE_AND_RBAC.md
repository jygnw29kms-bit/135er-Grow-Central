# Database, users and permissions

## Cloud / PostgreSQL

Core tables:

- `users`
- `roles`
- `permissions`
- `user_roles`
- `role_permissions`
- `sessions`
- `sites`
- `devices`
- `device_settings`
- `sensors`
- `sensor_readings`
- `schedules`
- `automations`
- `automation_rules`
- `events`
- `alerts`
- `commands`
- `command_results`
- `audit_log`
- `system_settings`
- `cloud_nodes`
- `backups`

## Local / SQLite

Local tables:

- `devices`
- `device_settings`
- `sensors`
- `sensor_readings_local`
- `schedules`
- `automations`
- `automation_rules`
- `events`
- `system_settings`
- `sync_state`

## Roles

### Administrator

Can:

- manage users/roles/permissions
- change system settings
- configure devices/sensors
- change schedules/automation
- manage cloud/backups
- read the audit log

### Operator

Can:

- control devices
- view sensor values
- edit schedules
- enable/disable automation
- view history

### Viewer

Read-only access to:

- dashboard
- sensor values
- history

### Device / Agent

Technical node role:

- write own telemetry
- report own state
- fetch allowed commands for itself
- return command results

## Permissions

Example granular permissions:

```text
users.read
users.write
roles.read
roles.write
sites.read
sites.write
devices.read
devices.control
devices.configure
sensors.read
sensors.configure
history.read
history.delete
schedules.read
schedules.write
automations.read
automations.write
automations.execute
alerts.read
alerts.manage
commands.create
commands.read
audit.read
system.read
system.write
backups.create
backups.restore
```

## Sessions

Sessions have:

- expiry
- optional refresh token
- revocation state
- IP/User-Agent metadata only where needed
- audit references for security-sensitive actions

## History

Sensor values require time-based indexes.

Retention can be configured per site or sensor:

- raw: e.g. 30–90 days
- aggregated 5-minute values: longer
- daily values: long term

Deletion actions are audited.
