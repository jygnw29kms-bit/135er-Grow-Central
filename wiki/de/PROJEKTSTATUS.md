# Projektstatus

**Phase:** v0.5.x Hardware Validation

## Fertig bzw. nachweisbar vorhanden

- FastAPI lokale Basis
- BLE Discovery
- Connect / Disconnect
- GATT Inspection
- GitHub-/CI-Imagebuilder-Basis
- Cloud-Telemetrie-/Historien-Alpha
- Responsive GUI-Zielbild
- SQLite-/PostgreSQL-Schema- und Plattformbaseline
- RBAC-/Rollenmodell

## Experimentell

- Notifications im DF100M-Kontext
- Raw BLE writes
- Speed-Payloads
- Cloud Command Flow

## Noch nicht als Runtime vollständig

- validiertes DF100M-Speed-Protokoll
- vollständige Benutzer-/Session-Authentisierung
- vollständige RBAC-Durchsetzung
- PostgreSQL-Produktivverdrahtung/Migrationsstack
- vollständiger Sensor-/Historienservice
- Schedule-/Automation-Engine
- Audit-Middleware
- WebSockets
- vollständiger Backup-/Restore-Betrieb

## Sichere Standards

```text
DF100M_ALLOW_WRITES=false
GC_REMOTE_COMMANDS=false
GC_CLOUD_ENABLED=false
```

## Nächster Meilenstein

Pi-Testimage erfolgreich bauen, flashen und reale DF100M-Discovery/GATT/Notification-Daten erfassen.
