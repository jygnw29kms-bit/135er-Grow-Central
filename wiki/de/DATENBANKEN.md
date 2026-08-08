# Datenbanken

## Lokal – SQLite

Für den Raspberry Pi:

- Geräte und Geräteeinstellungen
- Sensoren
- lokale Messwerte/Offline-Puffer
- Zeitpläne
- Automationsregeln
- Events
- Systemeinstellungen
- Sync-State

SQLite hält die lokale Instanz leichtgewichtig und unabhängig von der Cloud.

## Cloud – PostgreSQL

Für den VServer:

- users / roles / permissions / sessions
- sites
- devices / device_settings
- sensors / sensor_readings
- history
- schedules
- automations / automation_rules
- events / alerts
- commands / command_results
- audit_log
- system_settings
- cloud_nodes
- backups

## Grundregeln

- Foreign Keys verwenden
- Indizes auf Zeitstempel, Site, Device und Sensor
- UTC intern speichern
- Retention für hochfrequente Messwerte
- Migrationen versionieren
- Backup und Restore regelmäßig testen
