# 135er GrowControl – Deutsch

135er GrowControl ist eine **Local-First Steuer- und Überwachungsplattform** für einen Raspberry Pi mit optionaler Cloud auf einem Linux-VServer.

## Ziele

- lokale Gerätekommunikation ohne dauerhafte Hersteller-App
- zentrale Weboberfläche
- DF100M-BLE-Analyse und spätere Steuerung
- lokale Automationen auch ohne Internet
- optionale Cloud für Remote-Übersicht und Historie
- modulare Adapter für weitere Geräte

## Kernprinzipien

1. Der Raspberry Pi bleibt Master.
2. Die Cloud ist optional.
3. Remote-Befehle werden lokal nochmals geprüft.
4. Experimentelle BLE-Schreibbefehle sind standardmäßig deaktiviert.
5. Geräteprotokolle werden vom UI getrennt.
6. Quellen und Annahmen werden klar gekennzeichnet.

## Stand v0.4.1

- BLE Discovery: vorhanden
- Connect / Disconnect: vorhanden
- GATT Inspection: vorhanden
- Notifications: experimentell
- Speed Payload: nicht validiert
- Cloud Telemetrie: Alpha
- Cloud Historie: Alpha
- Remote Commands: vorbereitet, standardmäßig aus
- FC3000: geplant
- Sensorik / VPD: geplant
