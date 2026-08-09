# Architecture Master – 135er-Grow Central

## 1. Architectural goal

A local-first control platform in which loss of internet, cloud or vendor services does not remove local observability and automation.

## 2. Logical topology

```text
┌──────────────────────────── Clients ────────────────────────────┐
│ Browser · iPad · Tablet · Smartphone · Desktop                 │
└───────────────────────────────┬─────────────────────────────────┘
                                │ LAN HTTP/HTTPS
                                ▼
┌──────────────────── 135er-Grow Central Local ────────────────────┐
│ Raspberry Pi                                                   │
│                                                               │
│ FastAPI / Web UI                                              │
│ Device adapters                                               │
│ Local configuration                                           │
│ SQLite                                                        │
│ Schedules / automation target                                 │
│ Cloud-link agent                                              │
│                                                               │
│     BLE ─────────► DF100M                                     │
│     HTTPS outbound ─────────────────────────────────────┐      │
└─────────────────────────────────────────────────────────┼──────┘
                                                          │
                                                          ▼
                                  ┌──── Optional Linux VPS Cloud ────┐
                                  │ FastAPI/API                       │
                                  │ PostgreSQL target                 │
                                  │ Telemetry/history                 │
                                  │ Users/RBAC target                 │
                                  │ Remote overview                   │
                                  │ Command requests (opt-in)         │
                                  └───────────────────────────────────┘
```

## 3. Control authority

Priority order:

1. local safety / explicit local controls;
2. local schedules and automations;
3. validated optional cloud command requests.

The cloud must never become an implicit master.

## 4. Local data responsibility

SQLite is intended to retain enough data for independent operation:

- configuration;
- devices and local identities;
- schedules;
- automation rules;
- local sensor cache/history;
- event state;
- cloud synchronization state.

## 5. Cloud data responsibility

PostgreSQL is the target for:

- users, roles, permissions and sessions;
- sites and devices;
- consolidated sensor history;
- audit records;
- cloud nodes;
- remote command requests/results;
- backup metadata.

The current Alpha cloud runtime still uses simpler storage/auth in places; the target architecture must not be confused with runtime completeness.

## 6. Device adapter boundary

Device-specific protocol logic must be isolated from GUI/business logic. DF100M research belongs in an adapter/protocol layer so further devices can be added without redesigning the interface.

## 7. Network boundary

- No direct public exposure of Pi port 8080.
- VPS reverse proxy via Nginx/HTTPS.
- Pi cloud agent initiates HTTPS outbound.
- Remote commands are pulled/received as requests and validated locally.

## 8. Security controls

- systemd services with dedicated account;
- firewall baseline;
- unattended security upgrades;
- secrets in environment/config, not committed source;
- writes disabled until protocol validation;
- audit trail as platform requirement;
- role separation as platform requirement.

## 9. UI architecture target

The GUI is a responsive dark HUD with modules for Dashboard, Devices, Sensors, History, Schedules, Automations, Cloud and System. It must remain usable on an iPad 6th-generation-class viewport and modern phones/desktops.

## 10. Future runtime extensions

- PostgreSQL ORM/migrations;
- user login/session endpoints;
- RBAC enforcement middleware;
- sensor ingest/history queries;
- schedule/automation execution engine;
- audit middleware;
- WebSocket live updates;
- device heartbeat/offline state;
- executable backup/restore workflows.
