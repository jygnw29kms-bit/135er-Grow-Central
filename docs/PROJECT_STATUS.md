# Project Status – 135er-Grow Central

**Stand:** 2026-08-12

**Version:** alpha-0.7.4

**Phase:** platform consolidation + Raspberry Pi 3B first-boot validation + Mars Hydro/iConnect architecture alignment

A documented capability is not considered hardware-validated until it has been tested against the target device. Software integration can nevertheless be complete and CI-tested independently.

## Current hardware baseline

- **Mars Hydro FC3000, model year 2024, USB port, iConnect support**
- **Mars Hydro iFresh / DF100 series using iConnect**
- **DF100M / MZ_MZF002 BLE** retained as experimental diagnostics/reverse-engineering/fallback
- Raspberry Pi 3B as authoritative local master
- no ESP32 in the target architecture
- Logitech C920 as camera target
- Tapo, FRITZ!SmartHome, Shelly and Home Assistant as smart-home/power integration targets

## Current image result

The current Raspberry Pi image is reported by the project owner to be in a good state for its **first basic functions from first boot**. This is recorded as a positive alpha smoke-test result, not as full release validation.

Still requiring real target-hardware validation:

- repeatable fresh first boot and reboot behavior
- setup AP / DHCP / DNS reliability on physical Raspberry Pi networking
- provisioning transition and post-provisioning GUI availability
- Bluetooth initialization and device-name quality
- Logitech C920 capture path
- Mars Hydro FC3000 2024 iConnect communication
- Mars Hydro iFresh/DF100 iConnect communication
- DF100M BLE diagnostics and any write replay
- Tapo / FRITZ! / Shelly live device behavior
- power telemetry/history accuracy and cost calculations
- actuator failure modes and recovery

| Capability | Status | Notes |
|---|---|---|
| Local FastAPI | Implemented baseline | existing local service |
| First-boot AP/portal | Alpha smoke test positive | further repeatability/hardware validation required |
| GUI startup/recovery watchdog | Implemented baseline | image includes recovery path; repeated hardware test required |
| BLE discovery/connect/GATT | Implemented baseline | real-device validation ongoing |
| Bluetooth friendly naming | Implemented baseline | real-device quality check pending |
| Mars Hydro shared iConnect abstraction | Architecture baseline | FC3000 2024 + iFresh/DF100 are authoritative target family |
| FC3000 2024 iConnect control | Not validated | no guessed write path allowed |
| iFresh/DF100 iConnect control | Not validated | no guessed write path allowed |
| DF100M notification capture | Experimental | diagnostics/fallback only |
| DF100M speed protocol | Not validated | payload hypotheses only; writes deny-by-default |
| Local HUD | Implemented | responsive climate/device/power dashboard |
| Smart-home normalized models | Implemented | explicit inventory and adapter boundary |
| Smart-home device registry | Implemented | file-backed explicit inventory |
| Smart-home deny-by-default policy | Implemented | global + per-device gates |
| Local write-token helper | Implemented | fail-closed when unconfigured |
| Smart-home audit JSONL | Implemented baseline | DB migration future |
| Smart-plug overview API | Implemented | normalized safe-read telemetry |
| Smart-plug HUD | Implemented | ON/OFF, W, kWh, V, A, Hz and per-device status |
| Shelly Gen2+ | Implemented baseline | native local RPC; hardware test required |
| Home Assistant | Implemented baseline | connector hardware test required |
| Tapo | Bridge/discovery architecture | login/search/import hardware validation pending |
| FRITZ!SmartHome | Bridge architecture | real hardware validation pending |
| Apple Home / Siri | Bridge architecture | Home Assistant HomeKit Bridge |
| Logitech C920 | Image baseline | ffmpeg/v4l-utils + video group; capture test pending |
| Local SQLite | Baseline | persistent power time-series remains future work |
| Cloud FastAPI | Alpha | telemetry/history/commands baseline |
| Cloud PostgreSQL | Architecture baseline | runtime migration incomplete |
| Full RBAC/user sessions | Not complete | high-priority security work |
| Public project website | Implemented | static; deliberately has no local device API access |

## Security boundary

The public website never receives local device credentials, iConnect-related credentials, smart-plug credentials, local API tokens, or direct LAN endpoints. Live device data is served only by the local Raspberry Pi API or through explicitly approved server-side cloud synchronization. Every write path must remain authenticated, approved, writable, and audited.

## Immediate next milestones

1. repeat physical Raspberry Pi fresh-boot and reboot smoke tests;
2. verify AP/DHCP/provisioning-to-GUI transition without manual repair;
3. validate Logitech C920 enumeration and capture;
4. document the observable iConnect communication path for FC3000 2024 and iFresh/DF100 without guessing commands;
5. keep DF100M BLE tooling as diagnostics/fallback and capture real traffic only when needed;
6. hardware-test Shelly/Tapo/FRITZ!/Home Assistant paths;
7. persist power time-series and validate hour/day/week/month/year cost calculations;
8. complete user/session authentication and RBAC runtime;
9. continue image hardening and recovery testing before any beta designation.
