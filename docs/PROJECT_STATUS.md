# Project Status – 135er GrowControl

**Stand:** 2026-08-09  
**Phase:** v0.5.x Full Platform Baseline → Raspberry Pi / DF100M Hardware Validation

## Statusprinzip

Dieses Dokument ist die verbindliche Gegenmaßnahme gegen Überclaiming. Ein geplantes Datenmodell oder eine dokumentierte Plattformfunktion gilt nicht automatisch als fertig implementierte Runtime.

## Runtime-Matrix

| Capability | Status | Notes |
|---|---|---|
| Local FastAPI service | Implemented | `app/main.py` baseline |
| BLE discovery | Implemented | Bleak based |
| BLE connect/disconnect | Implemented | one client at a time |
| GATT inspection | Implemented | used for protocol research |
| Notification capture | Experimental | last notifications retained |
| Raw BLE writes | Experimental / guarded | disabled by default |
| DF100M percentage speed control | Not validated | payload modes are hypotheses |
| Local web UI | Implemented baseline | production HUD still evolving |
| Responsive GUI target | Defined | desktop/tablet/iPad/mobile |
| Local SQLite | Baseline | intended for local configuration/history/sync state |
| Cloud FastAPI | Alpha | telemetry/history/commands endpoints exist |
| Static cloud token auth | Alpha | not final user/session auth model |
| Cloud PostgreSQL runtime | Not complete | target/schema baseline exists |
| RBAC runtime | Not complete | role/permission model defined |
| User/session login | Not complete | future runtime work |
| Sensor history engine | Baseline | schema/domain direction defined |
| Schedule engine | Baseline | model direction defined |
| Automation engine | Baseline | model direction defined |
| Audit middleware/runtime | Not complete | schema/concept defined |
| WebSocket live data | Planned | not to be claimed as implemented |
| Backup/restore executable workflow | Partial/baseline | operational implementation still required |
| Pi cloud-link | Alpha | outbound HTTPS telemetry; commands opt-in |
| Remote commands | Prepared / disabled | local validation + dual opt-in concept |
| Pi 3B prebuilt image | Build pipeline in progress | GitHub Actions v2 workflow |

## Current DF100M facts

```text
Model focus:       DF100M
Legacy identifier: MZ_MZF002_0_A0A3B35EFDC8
Device ID:         A0A3B35EFDC8
Firmware:          V1.8
Working vendor UI: Mars Legacy app
```

Candidate BLE UUIDs remain experimental until hardware validation.

## Current safe defaults

```text
DF100M_ALLOW_WRITES=false
GC_REMOTE_COMMANDS=false
GC_CLOUD_ENABLED=false
```

## Test-image status

Target contents:

- Raspberry Pi OS Lite 64-bit / Debian 13
- hostname `growcontrol-test`
- temporary SSH login `test/test`
- token `test`
- BlueZ enabled
- GrowControl installed under `/opt/135er-growcontrol`
- systemd autostart
- ports 22 and 8080 permitted locally by UFW after first-boot initialization
- unattended security updates

Known build fixes:

1. root filesystem size/copy-loop issue fixed;
2. UFW chroot initialization replaced by first-boot service.

## Immediate next tasks

1. Complete successful image build and publish prerelease.
2. Flash image to Pi 3B/3B+.
3. Verify boot/network/SSH/UI/systemd/Bluetooth.
4. Capture real DF100M GATT and notification data.
5. Compare Legacy app behavior at controlled fan levels.
6. Validate write UUID and payload only after observation.
7. Update protocol state from candidate to observed/replayed/validated.
