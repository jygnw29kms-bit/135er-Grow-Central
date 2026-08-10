# Project Status – 135er-Grow Central

**Stand:** 2026-08-10

**Architecture:** alpha-0.7.1 Power Telemetry Integration

**Phase:** platform consolidation + Raspberry Pi / DF100M hardware validation

A documented capability is not considered hardware-validated until it has been tested against the target device. Software integration can nevertheless be complete and CI-tested independently.

| Capability | Status | Notes |
|---|---|---|
| Local FastAPI | Implemented baseline | existing local service |
| BLE discovery/connect/GATT | Implemented baseline | hardware validation pending |
| DF100M notification capture | Experimental | hardware validation required |
| DF100M speed protocol | Not validated | payload hypotheses only |
| Local HUD | Implemented | responsive climate/device/power dashboard |
| Smart-home normalized models | Implemented | explicit inventory and adapter boundary |
| Smart-home device registry | Implemented | file-backed explicit inventory |
| Smart-home deny-by-default policy | Implemented | global + per-device gates |
| Local write-token helper | Implemented | fail-closed when unconfigured |
| Smart-home audit JSONL | Implemented baseline | write actions audited; DB migration future |
| Smart-plug overview API | Implemented | `/api/v1/smarthome/overview` aggregates safe read telemetry |
| Smart-plug HUD | Implemented | ON/OFF, W, kWh, V, A, Hz and per-device status |
| Shelly Gen2+ switch + telemetry adapter | Implemented | native local RPC; hardware test required |
| Home Assistant switch + telemetry connector | Implemented | normalized attributes; hardware test required |
| Smart-plug protected control | Implemented | approval + writable flag + local API token + audit |
| Tapo | Bridge architecture | through Home Assistant |
| FRITZ!SmartHome | Bridge architecture | through Home Assistant |
| Apple Home / Siri | Bridge architecture | Home Assistant HomeKit Bridge |
| Native Matter bridge | Planned | after authentication/audit maturity |
| Local SQLite | Baseline | persistent power time-series remains future work |
| Cloud FastAPI | Alpha | telemetry/history/commands baseline |
| Cloud PostgreSQL | Architecture baseline | runtime migration incomplete |
| Full RBAC/user sessions | Not complete | high-priority security work |
| Pi 3B image | Build pipeline | workflow validation ongoing |
| Public project website | Implemented | static; deliberately has no local device API access |

## Security boundary for power devices

The public website never receives smart-plug credentials, local API tokens or direct LAN endpoints. Live power telemetry is served only by the local Raspberry Pi API. Read endpoints expose normalized operational values only; write endpoints remain authenticated and require both device approval and explicit write permission.

## Immediate next milestones

1. run CI against v0.7 code;
2. hardware-test Shelly local RPC telemetry;
3. test Home Assistant smart-plug telemetry in read-only mode;
4. connect real Tapo/FRITZ! entities through Home Assistant where required;
5. add persistent SQLite power time-series and chart history;
6. complete Pi image build;
7. validate DF100M BLE hardware;
8. implement user/session authentication and RBAC runtime;
9. migrate audit to structured persistence;
10. evaluate native Matter bridge.
