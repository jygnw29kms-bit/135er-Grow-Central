# Projektstatus

**Version:** `alpha-0.7.5`  
**Master:** `e339602`  
**Nächster Raspberry-Pi-Hardwaretest:** **Build 118**  
**Tag:** `pi-universal-alpha-0.7.5-118`  
**Status:** `CANDIDATE` – noch nicht hardwarevalidiert

Build 117 wurde erfolgreich getestet, ist durch den danach zusammengeführten e339-Stand jedoch überholt.

## Aktuell integriert

- Local-First FastAPI / GrowCentral GUI
- GrowCentral Nexus UI
- First Boot, Setup AP, LAN/WLAN und mDNS
- Geräte-Persistenz
- FRITZ! Smart Home
- lokales Tapo-Onboarding
- Räume, Pflanzen, Growtagebuch und Automation
- Energie-/Kostenlogik
- Logitech C920 / UVC, Snapshot, MJPEG und V4L2
- firmware-/modell-/USB-ID-bewusste Kamera-LED-Fähigkeitserkennung
- bedingte LED-Steuerung bei erkannter Unterstützung
- Elecrow 7-Zoll Touch-Kiosk
- Mobile Nexus Android + iOS Sideload Client
- Cloud Server V6
- signiertes APT Repository `https://repo.grow-central.de/apt`

## Experimentell / weiter zu validieren

- reale Gerätepfade je verfügbarer FRITZ!/Tapo-Hardware
- Mars Hydro iConnect
- DF100M BLE Diagnose/Reverse Engineering
- Kamera-LED-Funktion auf realer Zielkamera/Firmware
- Elecrow Kiosk auf Zielhardware

## Nächster Meilenstein

Build 118 booten und real prüfen: First Boot, Netzwerk, GUI, Persistenz, C920 inklusive LED-Fähigkeiten sowie relevante Geräte-/Displaypfade. Erst danach darf der Kandidat als `VALIDATED` markiert werden.

Kanonisch: [Release State](../../RELEASE_STATE.md) · [Build 118 Notes](../../docs/RELEASE_NOTES_BUILD_118.md) · [Release Pipeline](../../docs/RELEASE_PIPELINE.md)
