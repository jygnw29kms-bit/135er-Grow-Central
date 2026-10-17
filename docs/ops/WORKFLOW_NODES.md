# Produktiver Workflow der Projekt-Systeme

Stand: 2026-10-17

Diese Zuordnung ist verbindlich für Grow-Central und angrenzende Entwicklungs-, Test- und Deployment-Abläufe. Ziel ist klare Rollenverteilung, reproduzierbare Tests und möglichst wenig Doppelarbeit.

## Systeme und Rollen

### JensPC
Technischer Hostname: `DESKTOP-BNDD1US`

Rolle:
- zentrale Entwicklung und Orchestrierung
- Haupt-Checkouts und Branch-Arbeit
- Windows-Builds
- Python-/Node-Entwicklung
- statische Analyse, Unit- und Integrationstests
- Steuerung weiterer Testsysteme

Nicht vorgesehen:
- produktive Dauer-Services
- unnötige projektspezifische Zielhardware-Simulation, wenn echte Zielhardware vorhanden ist

### LucasPC
Technischer Hostname: `DESKTOP-SMN4ATU`

Rolle:
- UE5
- Blender
- GPU-lastige Arbeiten
- Grafik- und Asset-Pipeline
- visuelle Final-Master-Prüfung
- Game-Builds und Rendering

Für Grow-Central nur als zusätzlicher Windows-Gegenprüfer nutzen, wenn ein zweites Windows-System sinnvoll ist.

### Ayke-Root
Technischer Hostname: `server.hauptstadtgut8ten.info`

Rolle:
- unabhängige Linux-Validierung
- Staging
- containerisierte Prüfungen
- Web-/API-Tests
- reproduzierbare Linux-Builds
- zweite Validierungsstufe nach JensPC

Produktive Gameserver-/Hestia-Dienste dürfen durch Prüfläufe nicht gestört werden. Tests deshalb isoliert in temporären Arbeitsverzeichnissen oder Containern ausführen.

### Ete-Root
Technischer Hostname: `modest-babbage.87-106-119-187.plesk.page`

Rolle:
- Etes-Produktion
- Plesk
- Werkstattplaner/WerkstattControl Deployment
- produktionsnahe Smoke-Tests
- kleine, gezielte Deployment-Aufgaben

Kein allgemeiner CI- oder Build-Knoten. Bestehende Web-, Datenbank- und Plesk-Dienste haben Priorität.

### GrowPi
Technischer Hostname: `135er-grow-central`

Rolle:
- Grow-Central Zielsystem
- reale Sensorintegration
- MQTT
- HomeKit
- lokale Runtime
- Provisioning
- abschließende Hardware-/Integrationstests

Keine allgemeine Entwicklungs- oder CI-Maschine. Änderungen erst nach erfolgreicher Vorprüfung auf JensPC und Ayke-Root aufspielen.

### DysonPi
Technischer Hostname: `DysonPi`

Rolle:
- Dyson/BMS Hardware-Teststation
- I2C/UART/GPIO-nahe Tests
- DJI-/BMS-Experimente
- Printbench-nahe Hardwaretests

Keine allgemeinen Build- oder CI-Aufgaben.

## Verbindliche Prüf-Reihenfolge

Vor produktiven Änderungen gilt grundsätzlich:

1. analysieren
2. bestehenden Zustand prüfen
3. Auswirkungen bewerten
4. Ursache und Ziel verifizieren
5. Änderung optimieren/implementieren
6. auf JensPC testen
7. erneut analysieren
8. auf Ayke-Root Linux-seitig gegenprüfen, sofern technisch sinnvoll
9. GitHub CI prüfen
10. projektspezifisches Zielsystem testen
11. erst danach produktiv ausrollen

## Grow-Central Pipeline

`GitHub -> JensPC -> Ayke-Root -> GrowPi -> Produktion`

- JensPC: Entwicklung, Unit-/Integrationstests und Codeanalyse
- Ayke-Root: unabhängiger Linux-Gegencheck in isolierter Umgebung
- GrowPi: echte MQTT-, Sensor-, HomeKit- und Runtime-Prüfung
- Live-Deployment nur nach erfolgreicher Validierung

## Grundregeln

- Keine ungetesteten Änderungen direkt auf Produktionssystemen.
- Keine Projektdateien zwischen Rechnern kopieren, wenn Git die Quelle sein kann.
- Jeder Knoten hat eine klar abgegrenzte Rolle.
- Zielhardware wird für echte Integrationstests genutzt, nicht als Entwicklungsarbeitsplatz.
- Build-Artefakte und temporäre Checkouts auf Servern werden nach erfolgreicher Prüfung wieder entfernt.
- Produktionsdienste haben Vorrang vor Testjobs.
- Hardware-Erweiterungen sind aktuell nicht Bestandteil der Workflow-Optimierung.
