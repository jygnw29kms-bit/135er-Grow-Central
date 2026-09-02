# Project Status – 135er-Grow Central

- **Stand:** 2. September 2026
- **Version:** `alpha-0.7.5`
- **Branch:** `master`
- **Aktueller Pi-Candidate:** **Build 199**
- **Status:** `CANDIDATE` – reale Hardwarevalidierung offen
- **Entwicklungsmodus:** geschlossen

Kanonische Quellen: [Release State](../RELEASE_STATE.md) und [Hardware Support Policy](HARDWARE_SUPPORT_POLICY.md).

## Verbindliche Architektur

- dauerhaft headless; kein lokaler Kiosk oder Desktop;
- lokale Raspberry-Pi-Instanz bleibt Geräteautorität;
- Desktop-Weboberfläche und eigenständige Mobile-Oberfläche;
- optionale Cloud ohne Abhängigkeit der lokalen Kernfunktionen;
- ein Universal-Image mit zentraler Hardwareerkennung.

## Hardwareklassen

- Pi 3B/3B+ → `LEGACY_LITE`, weiterhin unterstützt;
- Pi 4/400/CM4 → `FULL_SUPPORT` Standard, empfohlen;
- Pi 5/CM5 → `FULL_SUPPORT` Performance.

## Aktueller Funktionsstand

| Bereich | Stand |
|---|---|
| Headless Local Runtime | implementiert |
| Hardwareprofil-Runtime | implementiert und getestet |
| First Boot / Setup-AP | implementiert, realer Wiederholungstest offen |
| LAN / WLAN / mDNS | implementiert, reale Persistenzprüfung offen |
| Desktop Command Center | implementiert |
| Mobile GUI | implementiert; iOS-WebKit-Scrollfix in Build 199 |
| Räume / Grow / Automationen | Baseline implementiert |
| Geräteplattform | Baseline und Providerpfade implementiert |
| FRITZ!, Tapo, Shelly, Home Assistant | Integrationspfade vorhanden |
| Tuya, Zigbee2MQTT, MQTT, ESP32 | Providerpfade vorhanden |
| Spider Farmer / Mars Hydro | Telemetriepfade vorhanden; Writes nur nach Validierung |
| Logitech C920 / UVC | capability-abhängige Kamera-Baseline |
| Cloud-Link | optionaler, authentifizierter Pfad |
| Mobile-Pakete | interne iOS-/Android-Testpakete |
| Website | öffentliche Marketingseite ohne interne Downloads |

Eine vorhandene Provider-Implementierung ist keine pauschale Hardwarefreigabe. Modell-, Firmware- und Schreibpfade bleiben separat zu validieren.

## Nächster Meilenstein

Build 199 muss auf realer Zielhardware geprüft werden. Erst danach darf die jeweilige Hardwareklasse als `VALIDATED` markiert werden. Neue Builds und Artefakte werden bis auf Weiteres nicht öffentlich verteilt.
