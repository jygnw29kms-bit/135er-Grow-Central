# Architektur

## Leitprinzip

135er-Grow Central ist **local-first**.

```text
Browser / iPad
      │
      ▼
FastAPI + Web UI
      │
      ├── Device Registry
      ├── Automation Engine
      ├── Event Store
      └── MQTT
             │
             ▼
       Device Adapter
             │
          Bluetooth LE
             │
             ▼
        Mars Hydro DF100M
```

## Warum Raspberry Pi statt ESP32?

Die Referenz `KillerInk/GrowFanController` nutzt einen ESP32 als Controller. 135er-Grow Central übernimmt dagegen die komplette Softwarelogik auf dem Raspberry Pi.

Vorteile:

- Python/Bleak für BLE-Reverse-Engineering
- umfangreichere Webplattform
- SQLite
- systemd
- leichter erweiterbare Adapter
- Docker später möglich
- direkter Home-Assistant-/MQTT-Anschluss

## Schichten

### UI

`web/`

Keine Geräteprotokollkenntnis.

### API

`app/api/`

HTTP-Endpunkte für das Frontend.

### Adapter

`app/devices/`

Enthält gerätespezifische Kommunikation.

### Persistenz

`app/db/`

Mess- und Ereignisdaten.

### Automation

zukünftiges Modul.

Die Automation kommuniziert nicht direkt mit BLE, sondern immer über den Adapter.

## Quellen

Siehe [SOURCES.md](SOURCES.md).
