# Project Status – 135er GrowControl

**Stand:** 2026-08-09  
**Architecture:** v0.6 Secure Smart-Home Platform  
**Phase:** platform consolidation + Raspberry Pi / DF100M hardware validation

A documented capability is not considered runtime-complete until code, tests and operating documentation exist.

| Capability | Status | Notes |
|---|---|---|
| Local FastAPI | Implemented baseline | existing local service |
| BLE discovery/connect/GATT | Implemented baseline | hardware validation pending |
| DF100M notification capture | Experimental | hardware validation required |
| DF100M speed protocol | Not validated | payload hypotheses only |
| Local HUD | Implemented baseline | API alignment/security refinement ongoing |
| Smart-home normalized models | Implemented baseline | v0.6 |
| Smart-home device registry | Implemented baseline | file-backed explicit inventory |
| Smart-home deny-by-default policy | Implemented baseline | global + per-device gates |
| Local write-token helper | Implemented baseline | fail-closed when unconfigured |
| Smart-home audit JSONL | Implemented baseline | DB-backed audit remains future work |
| Shelly Gen2+ switch adapter | Implemented baseline | hardware test required |
| Home Assistant switch connector | Implemented baseline | hardware test required |
| Tapo | Bridge architecture | through Home Assistant |
| FRITZ!SmartHome | Bridge architecture | through Home Assistant |
| Apple Home / Siri | Bridge architecture | Home Assistant HomeKit Bridge |
| Native Matter bridge | Planned | after authentication/audit maturity |
| Local SQLite | Baseline | existing direction |
| Cloud FastAPI | Alpha | telemetry/history/commands baseline |
| Cloud PostgreSQL | Architecture baseline | runtime migration incomplete |
| Full RBAC/user sessions | Not complete | high-priority security work |
| Pi 3B image | Build pipeline | workflow validation ongoing |
| Public project website | Implemented | GitHub Pages workflow added |

## Immediate next milestones

1. run CI against v0.6 code;
2. complete Pi image build;
3. validate DF100M BLE hardware;
4. hardware-test Shelly local RPC;
5. test Home Assistant connector with read-only mode first;
6. add Tapo and FRITZ! entities through Home Assistant;
7. expose selected GrowControl entities to Apple Home through HomeKit Bridge;
8. implement user/session authentication and RBAC runtime;
9. migrate audit to structured persistence;
10. evaluate native Matter bridge.
