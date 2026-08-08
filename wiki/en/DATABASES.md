# Databases

Local Raspberry Pi uses SQLite for devices, local sensor data, schedules, automations, events, settings and sync state.

Cloud uses PostgreSQL for users/RBAC, sites, devices, sensors/readings, history, schedules, automations, events/alerts, commands/results, audit log, settings, cloud nodes and backups.

Use foreign keys, useful indexes, UTC timestamps, retention rules, versioned migrations and tested backups.
