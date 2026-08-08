# Backup und Wartung

## Regelmäßig

- `apt update` / Sicherheitsupdates überwachen
- Service-Status prüfen
- Datenbankgröße und Retention kontrollieren
- Zertifikatsstatus prüfen
- Backup-Erfolg kontrollieren
- Audit-/Fehlerlogs auf Auffälligkeiten prüfen

## Backup

Cloud: PostgreSQL-Dump plus Konfiguration/Secrets getrennt sichern.

Local: SQLite-Datenbank, lokale Konfiguration, Zeitpläne und Automationsregeln sichern.

## Restore

Restore-Prozeduren müssen getestet sein. Nach Wiederherstellung werden Dateirechte, systemd-Services, Datenbankmigrationen und Healthchecks geprüft.
