# Project Status

**Phase:** v0.5.x Hardware Validation

Implemented runtime baseline includes local FastAPI, BLE discovery/connect/disconnect, GATT inspection and an Alpha cloud telemetry/history path. Notification handling and BLE writes are experimental. The DF100M speed protocol is not yet validated.

Platform baselines exist for SQLite/PostgreSQL data models, RBAC, sensors/history, schedules, automations, events, alerts, commands, audit and backups; these must not be interpreted as fully completed production runtime features.

Safe defaults:

```text
DF100M_ALLOW_WRITES=false
GC_REMOTE_COMMANDS=false
GC_CLOUD_ENABLED=false
```

Next milestone: successful Raspberry Pi test-image build, physical boot verification and real DF100M GATT/notification capture.
