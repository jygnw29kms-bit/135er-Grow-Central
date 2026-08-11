# 135er-Grow Central · Dokumentation (Deutsch)

[English](../en/README.md) · [Dokumentationszentrum](../README.md) · [Repository](../../README.md)

135er-Grow Central ist eine **Local-First Steuer- und Überwachungsplattform** für einen Raspberry Pi mit optionaler Cloud auf einem Linux-VServer.

## Ziele

- lokale Gerätekommunikation ohne dauerhafte Hersteller-App
- zentrale responsive Weboberfläche
- DF100M-BLE-Analyse und spätere Steuerung
- lokale Automationen auch ohne Internet
- optionale Cloud für Remote-Übersicht und Historie
- modulare Adapter für weitere Geräte
- reproduzierbare Raspberry-Pi-Testimages für Hardwaretests

## Kernprinzipien

1. Der Raspberry Pi bleibt Master.
2. Die Cloud ist optional.
3. Remote-Befehle werden lokal nochmals geprüft.
4. Experimentelle BLE-Schreibbefehle sind standardmäßig deaktiviert.
5. Geräteprotokolle werden vom UI getrennt.
6. Quellen und Annahmen werden klar gekennzeichnet.
7. Große Systemimages werden als Release-/Actions-Artefakte statt in der normalen Git-Historie veröffentlicht.

## Stand alpha-0.7.1 · Hardware-Validierung

- BLE Discovery: vorhanden
- Connect / Disconnect: vorhanden
- GATT Inspection: vorhanden
- Notifications: experimentell
- DF100M Speed Payload: nicht validiert
- Cloud Telemetrie / Historie: Alpha
- Remote Commands: vorbereitet, standardmäßig aus
- Full-Platform-Datenmodell und RBAC: definiert
- Debian/Ubuntu/Raspberry-Pi-Installer-Baseline: vorhanden
- GUI-Zielbild und Responsive-Regeln: definiert
- Raspberry Pi 3B/3B+ Image-Builder: vorhanden
- vorinstalliertes Pi-Testimage: Build-/Testphase
- FC3000: geplant
- Sensorik / VPD: Plattform vorbereitet

## Aktuelle Testdokumentation

- [Raspberry Pi 3B Test-Image](RASPBERRY_PI_3B_TEST_IMAGE.md)
- [GUI-Zielbild](GUI_VORSCHAU.md)
- [DF100M-Protokollanalyse](DF100M_PROTOCOL.md)
- [Cloud](CLOUD.md)
- [Installation](INSTALLATION.md)

Das Test-Image startet beim ersten Boot den geschützten Zugangspunkt `135er-GrowCentral-Setup-XXXX`. Die temporären Zugangsdaten `GrowCentral` / `grow-central-test` gelten für WLAN, Portal und SSH; das Portal erzwingt vor dem Hauptsystemstart ein neues Gerätepasswort. Die Anwendungstoken bleiben während der Hardwaretests auf `test` und müssen vor einem produktiven Einsatz ersetzt werden.
