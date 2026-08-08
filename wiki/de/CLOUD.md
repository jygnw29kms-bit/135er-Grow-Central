# Cloud

Die Cloud ist optional. Lokale Steuerung funktioniert ohne VServer weiter.

## Aufgaben

- Telemetrieannahme
- langfristige Historie
- Benutzer/RBAC
- Multi-Site-Übersicht
- Command Queue
- Audit und Backups

## Verbindung

Der Raspberry Pi baut die Verbindung ausgehend per HTTPS auf. Es wird kein lokaler Steuerport ins Internet veröffentlicht.

## Remote Commands

Remote Commands benötigen doppelte Freigabe:

- Cloud: Commands erlaubt
- Local: Remote Commands erlaubt

Der Pi prüft Ziel, Aktion und Wert erneut lokal. Abgelaufene oder ungültige Commands werden verworfen.
