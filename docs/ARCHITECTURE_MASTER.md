# Architecture Master – 135er-Grow Central

## 1. Architectural goal

A local-first control platform in which loss of internet, cloud, or vendor services does not remove local observability and automation. The Raspberry Pi is the authoritative local master.

## 2. Logical topology

```text
┌──────────────────────────── Clients ────────────────────────────┐
│ Browser · iPad · Tablet · Smartphone · Desktop                │
└───────────────────────────────┬─────────────────────────────────┘
                                │ LAN HTTP/HTTPS
                                ▼
┌──────────────────── 135er-Grow Central Local ──────────────────┐
│ Raspberry Pi 3B                                               │
│                                                              │
│ FastAPI / Web UI                                             │
│ Device adapters / policy / audit                            │
│ Local configuration / SQLite                               │
│ Schedules / automation target                             │
│ Cloud-link agent                                         │
│                                                        │
│ Mars Hydro/iConnect abstraction                        │
│   ├─ FC3000 2024 · USB · iConnect                    │
│   ├─ iFresh / DF100 · iConnect                      │
│   └─ DF100M BLE diagnostics/fallback               │
│                                                   │
│ Smart home / power                                  │
│   ├─ Shelly Gen2+ local JSON-RPC                    │
│   ├─ Tapo / FRITZ! via validated local/HA paths    │
│   └─ Home Assistant bridge                          │
│                                                    │
│ Camera: Logitech C920 local Linux video stack      │
│                                                    │
│ HTTPS outbound ───────────────────────────────┐     │
└───────────────────────────────────────────────┼─────┘
                                                │
                                                ▼
                               ┌── Optional Linux VPS Cloud ──┐
                               │ FastAPI/API                  │
                               │ PostgreSQL target            │
                               │ Telemetry/history            │
                               │ Users/RBAC target            │
                               │ Remote overview              │
                               │ Command requests (opt-in)    │
                               └──────────────────────────────┘
```

## 3. Authoritative hardware definitions

- **Mars Hydro FC3000** means the **2024 model with USB port and iConnect support**.
- **DF100** means the **Mars Hydro iFresh series using iConnect**.
- Existing **DF100M / MZ_MZF002** BLE code is an experimental diagnostics/reverse-engineering/fallback path, not the primary ecosystem architecture.
- **ESP32 is excluded** from the target architecture.
- Logitech C920 is the reference camera target currently prepared in the image.

## 4. Control authority

Priority order:

1. local safety / explicit local controls;
2. local schedules and automations;
3. validated optional cloud command requests.

The cloud must never become an implicit master. Vendor-cloud paths must not be able to bypass local device approval, authentication, writable flags, or audit.

## 5. Device adapter boundary

Device-specific protocol logic is isolated from GUI/business logic. The Mars Hydro layer must expose normalized capabilities without pretending unvalidated features exist. No guessed iConnect write protocol is permitted.

The current DF100M BLE tooling remains useful for discovery, GATT inspection, notification capture, and controlled protocol research. Its compatibility endpoints may remain while the primary Mars Hydro/iConnect adapter is developed.

## 6. Local data responsibility

SQLite is intended to retain enough data for independent operation:

- configuration;
- devices and local identities;
- schedules;
- automation rules;
- local sensor cache/history;
- power telemetry and cost history;
- event state;
- cloud synchronization state.

## 7. Cloud data responsibility

PostgreSQL is the target for users/RBAC, sites/devices, consolidated history, audit records, cloud nodes, remote command requests/results, and backup metadata. Current Alpha runtime completeness must not be confused with the target architecture.

## 8. Network boundary

- No direct public exposure of the Pi GUI ports 80 or 8080.
- Pi cloud communication is outbound HTTPS.
- Remote commands are treated as requests and validated locally.
- First boot uses the dedicated provisioning AP and portal; main UI availability must recover even if provisioning fails.
- Bluetooth device presentation should prefer readable advertised names and conservative type hints over raw MAC addresses.

## 9. Security controls

- dedicated systemd service account;
- firewall baseline;
- unattended security upgrades;
- secrets in environment/config, not committed source;
- device writes deny-by-default until protocol validation;
- audit trail as platform requirement;
- role separation as platform requirement;
- public website has no device-control credentials or local API access.

## 10. UI architecture target

The GUI is a responsive dark HUD / control-room interface shared by Website, local GUI, cloud GUI, and project previews. It must remain usable on an iPad 6th-generation-class viewport, phones, tablets, and desktops. PNG is the runtime image format preference; WebP is not used.

The GUI must support normalized device status, power values, kWh history, hour/day/week/month/year views, and user-defined electricity cost projection. Concept preview values must remain clearly distinguishable from validated live telemetry.

## 11. Current image validation state

The current Raspberry Pi image has been reported as looking good in the first basic functions from first boot. This is recorded as a positive Alpha smoke-test result only. Repeated physical tests for AP/DHCP, provisioning transition, GUI recovery, Bluetooth, camera, smart-home hardware, and Mars Hydro/iConnect communication remain required.

## 12. Future runtime extensions

- validated Mars Hydro/iConnect adapter;
- persistent power time-series and cost calculations;
- user login/session endpoints;
- RBAC enforcement middleware;
- sensor ingest/history queries;
- schedule/automation execution engine;
- audit persistence;
- WebSocket live updates;
- device heartbeat/offline state;
- executable backup/restore workflows;
- Matter only after authentication/audit maturity.
