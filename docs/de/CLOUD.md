# Grow Central Cloud

Die Cloud läuft optional auf einem Linux-VServer.

## Aufgaben

- Telemetrie empfangen
- Historie speichern
- letzten Standortzustand darstellen
- Remote Dashboard bereitstellen
- vorbereitete Command Queue

## Sicherheit

Remote Commands brauchen zwei Freigaben:

1. `CLOUD_ALLOW_COMMANDS=true` auf dem Server
2. `GC_REMOTE_COMMANDS=true` auf dem Pi

Der Pi prüft Befehle nochmals lokal.
