# Benutzer, Rollen und Rechte

## Rollenmodell

### Administrator
Vollzugriff auf Benutzer, Rollen, System, Geräte, Sensoren, Zeitpläne, Automationen, Historie, Cloud und Audit-Log.

### Operator
Darf Geräte bedienen, Sensorwerte ansehen, Zeitpläne und Automationen verwalten sowie Historie einsehen.

### Viewer
Nur lesender Zugriff auf Dashboard, Sensorwerte und Historie.

### Device/Agent
Technische Rolle für Telemetrie, Heartbeat und freigegebene Command-Verarbeitung.

## Datenmodell

- `users`
- `roles`
- `permissions`
- `user_roles`
- `role_permissions`
- `sessions`

Rechte werden nicht nur im Frontend versteckt, sondern serverseitig an jedem geschützten API-Endpunkt geprüft.
