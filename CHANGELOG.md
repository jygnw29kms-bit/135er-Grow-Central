# Changelog

All notable changes to 135er GrowControl are documented here. Status labels distinguish runtime-complete features from architecture/design baselines.

## Unreleased / Hardware Test Phase – 2026-08

### Added
- Reproducible Raspberry Pi 3B/3B+ test-image workflow based on Raspberry Pi OS Lite 64-bit / Debian 13.
- Temporary hardware-test credentials `test/test` and test token `test` for isolated test environments.
- Dedicated `growcontrol` service account and systemd autostart for local GrowControl.
- First-boot UFW initialization service because UFW cannot be reliably initialized inside the GitHub ARM chroot.
- Professional project-record documentation: project history, status matrix, master architecture, DF100M research log, hardware test plan, security/trust model, decision log and image/release process.
- Versioned Wiki source under `wiki/`.
- PNG GUI preview for reliable GitHub rendering.

### Changed
- GUI preview references changed from WebP to PNG.
- Project naming consolidated to **135er GrowControl**; DF100M is treated only as a device/model identifier.
- Platform direction consolidated around Raspberry Pi/Debian/Ubuntu; ESP32 excluded from core design.
- Cloud architecture clarified as optional outbound HTTPS extension, never local master.

### Fixed
- Image builder no longer copies downloaded `.img/.img.xz` build artifacts into target root filesystem.
- Image builder expands the image and root partition before package/project installation.
- UFW setup deferred to first physical Raspberry Pi boot to avoid chroot iptables detection failure.

### Security
- DF100M writes remain disabled by default.
- Remote cloud commands remain disabled by default.
- Test credentials are explicitly documented as temporary and unsuitable for untrusted networks.

## v0.5 Full Platform Baseline

### Added
- Full-platform architecture baseline.
- Local SQLite and cloud PostgreSQL schema direction.
- RBAC roles: Admin, Operator, Viewer, Device/Agent.
- Domain models for sites, devices, sensors, history, schedules, automations, events, alerts, commands, audit logging, settings, cloud nodes and backups.
- Installer/hardening baseline for Debian/Ubuntu/Raspberry Pi OS.
- Responsive GUI design reference and DE/EN documentation.

### Clarification
- v0.5 defines and scaffolds platform capabilities; it does **not** mean all planned RBAC, PostgreSQL, migrations, WebSockets, sensor automation or backup functions are runtime-complete.

## v0.4.1 Local/Cloud/BLE Baseline

### Added
- FastAPI local runtime.
- BLE discovery/connect/disconnect using Bleak.
- GATT inspection and notification capture.
- Experimental speed/raw write endpoints with write protection.
- Optional cloud telemetry/history Alpha.
- Prepared command request/result flow.
- Pi cloud-link agent with outbound HTTPS model.

## Early prototypes

- Initial Raspberry Pi fan-control exploration.
- Mars Legacy APK observations and DF100M candidate UUID research.
- GUI evolution from early test view to futuristic responsive HUD direction.
- KillerInk/GrowFanController used as inspiration only; ESP32 functionality intentionally not adopted.
