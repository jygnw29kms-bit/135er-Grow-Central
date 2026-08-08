# Architektur

```text
Browser / iPad
      │
      ▼
GrowControl Local UI
      │
      ▼
FastAPI auf Raspberry Pi
      │
      ├── BLE ──► DF100M
      ├── lokale Daten / spätere Automationen
      └── Cloud Link ──HTTPS──► Linux VServer
                                  ├── Telemetrie
                                  ├── Historie
                                  └── Remote Übersicht
```

## Local-First

Zeitpläne, Klimaautomationen und Gerätesteuerung sollen vollständig lokal ausführbar sein.

## Cloud

Die Cloud darf kein Single Point of Failure sein. Sie erhält Telemetrie und stellt Remote-Daten bereit.

## Adapter-Prinzip

Gerätespezifische Protokolllogik gehört in Adapter. UI, Automation und Cloud arbeiten mit normalisierten Zuständen.
