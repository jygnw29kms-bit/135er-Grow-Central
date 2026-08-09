# Architektur

```text
Browser / iPad / Smartphone
          |
          v
135er-Grow Central Local
Raspberry Pi / Debian-basiert
  |       |        |
  |       |        +-- SQLite / lokale Daten
  |       +----------- Automation Engine / Zeitpläne
  +------------------- BLE -> DF100M / weitere Adapter
          |
          +-- ausgehendes HTTPS --> Grow Central Cloud
                                   Debian/Ubuntu VServer
                                   PostgreSQL / API / Historie
```

## Local-First

Der Raspberry Pi führt lokale Zeitpläne, Automationen und Gerätezugriffe unabhängig vom VServer aus. Fällt Internet oder Cloud aus, bleibt der lokale Betrieb erhalten.

## Cloud

Die Cloud übernimmt optionale zentrale Funktionen: Benutzerverwaltung, längerfristige Historie, standortübergreifende Übersicht, Remote-Status und freigegebene Remote-Commands.

## Datenfluss

1. Sensor oder Geräteadapter erzeugt Telemetrie.
2. Lokale Datenbank speichert den aktuellen Zustand und Offline-Puffer.
3. Automation Engine bewertet Regeln lokal.
4. Cloud-Link überträgt Telemetrie ausschließlich ausgehend per HTTPS.
5. Remote-Commands werden nur bei aktivierter Server- und Local-Freigabe übernommen.
6. Jede Aktion wird validiert und auditierbar protokolliert.
