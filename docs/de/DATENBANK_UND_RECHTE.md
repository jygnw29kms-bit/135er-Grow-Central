# Datenbank, Benutzer und Rechte

## Cloud / PostgreSQL

Zentrale Tabellen:

- `users`
- `roles`
- `permissions`
- `user_roles`
- `role_permissions`
- `sessions`
- `sites`
- `devices`
- `device_settings`
- `sensors`
- `sensor_readings`
- `schedules`
- `automations`
- `automation_rules`
- `events`
- `alerts`
- `commands`
- `command_results`
- `audit_log`
- `system_settings`
- `cloud_nodes`
- `backups`

## Local / SQLite

Lokale Tabellen:

- `devices`
- `device_settings`
- `sensors`
- `sensor_readings_local`
- `schedules`
- `automations`
- `automation_rules`
- `events`
- `system_settings`
- `sync_state`

## Rollen

### Administrator

Darf:

- Benutzer/Rollen/Rechte verwalten
- Systemeinstellungen ändern
- Geräte/Sensoren konfigurieren
- Zeitpläne/Automationen ändern
- Cloud/Backups verwalten
- Audit-Log lesen

### Operator

Darf:

- Geräte bedienen
- Sensorwerte sehen
- Zeitpläne bearbeiten
- Automationen aktivieren/deaktivieren
- Historie sehen

### Viewer

Darf nur lesen:

- Dashboard
- Sensorwerte
- Historie

### Device / Agent

Technische Rolle für Nodes:

- eigene Telemetrie schreiben
- eigenen Status melden
- eigene freigegebene Commands abrufen
- Command-Ergebnisse zurückmelden

## Permissions

Beispielhafte granularen Rechte:

```text
users.read
users.write
roles.read
roles.write
sites.read
sites.write
devices.read
devices.control
devices.configure
sensors.read
sensors.configure
history.read
history.delete
schedules.read
schedules.write
automations.read
automations.write
automations.execute
alerts.read
alerts.manage
commands.create
commands.read
audit.read
system.read
system.write
backups.create
backups.restore
```

## Sessions

Sessions erhalten:

- Ablaufzeit
- optional Refresh-Token
- Widerrufsstatus
- IP/User-Agent-Metadaten nur soweit erforderlich
- Audit-Referenz für sicherheitsrelevante Aktionen

## Historie

Sensorwerte müssen zeitbasiert indiziert werden.

Retention wird pro Site oder Sensor definierbar:

- Raw: z. B. 30–90 Tage
- verdichtete 5-Minuten-Werte: länger
- Tageswerte: langfristig

Löschvorgänge werden auditiert.
