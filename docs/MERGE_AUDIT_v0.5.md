# Merge Audit – v0.4.1 + Full Platform v0.5

## DE

Basis ist `master` mit Commit `635e8c2e785050c0814b02481bddd224d502f19d` (v0.4.1 DE/EN + Cloud).

Geprüft und unverändert beibehalten:

- Local-First Raspberry-Pi-Architektur
- DF100M BLE Discovery / Connect / GATT / Notify Testpfad
- experimentelle BLE-Schreibzugriffe standardmäßig deaktiviert
- lokale Future-HUD-Weboberfläche
- Cloud-FastAPI-Grundlage
- Cloud-Link vom Pi zum VServer
- SQLite-Telemetrie-Alpha
- zweisprachige DE/EN-Dokumentation
- Docker/Nginx/systemd-Grundlagen

Zusammengeführt bzw. ergänzt:

- Debian/Ubuntu als verbindliche Plattformbasis
- vollständiges Installer-/Update-/Backup-/Restore-Konzept
- APT-Härtung und unattended-upgrades
- Domain, Nginx, TLS/Let's Encrypt
- Firewall und Fail2ban
- dedizierter Service-User und Dateirechte
- RBAC: Benutzer, Rollen, Rechte, Sessions
- Sites, Geräte, Sensoren, Messwerte
- Historie und Retention
- Zeitpläne und Automation Engine
- Events, Alerts und Audit-Log
- PostgreSQL für Cloud, SQLite lokal
- sichere Remote-Command-Doppelfreigabe
- Offline-Pufferung und Sync-State

Der Branch entfernt keine v0.4.1-Funktionalität.

## EN

The base is `master` at commit `635e8c2e785050c0814b02481bddd224d502f19d` (v0.4.1 DE/EN + Cloud).

Preserved without removal:

- local-first Raspberry Pi architecture
- DF100M BLE discovery/connect/GATT/notify test path
- experimental BLE writes disabled by default
- local Future HUD
- cloud FastAPI foundation
- Pi-to-VPS cloud link
- SQLite telemetry alpha
- bilingual DE/EN documentation
- Docker/Nginx/systemd foundations

Merged/added:

- Debian/Ubuntu as the supported OS family
- complete installer/update/backup/restore concept
- APT hardening and unattended upgrades
- domain, Nginx and TLS/Let's Encrypt
- firewall and Fail2ban
- dedicated service user and file permissions
- RBAC: users, roles, permissions and sessions
- sites, devices, sensors and readings
- history and retention
- schedules and automation engine
- events, alerts and audit log
- PostgreSQL for cloud, SQLite locally
- secure dual opt-in for remote commands
- offline buffering and sync state

No v0.4.1 functionality is intentionally removed by this branch.
