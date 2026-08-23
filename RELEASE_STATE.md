# 135er-Grow Central · Canonical Release State

**Stand:** 2026-08-23  
**Repository-Version:** `alpha-0.7.5`  
**Branch:** `master`  
**Current master anchor:** `e339602476f3a716ae28abd5334cb6f96447a646`  
**Next Raspberry-Pi hardware-test candidate:** **Build 118**  
**Candidate tag:** `pi-universal-alpha-0.7.5-118`

> Diese Datei ist die kanonische Referenz für README, Website, Pi-Image, Mobile, Cloud/APT und Release-Dokumentation. Historische Build-Dokumente dürfen ältere Nummern enthalten, müssen aber als Historie verstanden werden.

## Statusmodell

- **Build 117:** vorheriger erfolgreich getesteter Image-Stand; durch den zusammengeführten `e339`-Stand funktional überholt.
- **Build 118:** aktueller Kandidat für den nächsten realen Hardwaretest. **Noch nicht als hardwarevalidiert markieren**, bis der Test auf dem Raspberry Pi abgeschlossen ist.
- **Stable:** weiterhin nicht freigegeben; Projekt bleibt `alpha-0.7.5`.

## In Build 118 zusammengeführt

- aktueller GrowCentral Nexus UI / Repo-Designstand;
- Raspberry-Pi Local-First GUI, First Boot, Netzwerk, FRITZ! und Tapo;
- Logitech-C920/UVC-Pfad;
- firmware-/modell-/USB-ID-bewusste Kamera-LED-Fähigkeitserkennung;
- bedingte V4L2-/Logitech-LED-Steuerung statt blindem Schreiben;
- Tests für die LED-Fähigkeits- und Steuersemantik;
- Elecrow 7-Zoll Touch-Kiosk inklusive systemd-Service und gehärteten Dateirechten;
- Räume/Grow, Automationen, Diagnose und Supportpfade;
- Mobile Nexus Clients für Android und iOS-Sideloading;
- Cloud Server V6 und signierter APT-Pfad.

## Release-Gates

1. automatisierte Python-/Security-/Integrationsprüfungen;
2. Pi-Image aus dem aktuellen `master` erzeugen;
3. Image booten und rebooten;
4. First Boot, LAN/WLAN/AP, GUI und Persistenz prüfen;
5. C920 inkl. LED-Fähigkeiten auf realer Hardware prüfen;
6. relevante FRITZ!/Tapo/Mars-Hydro-/Displaypfade prüfen;
7. Support-Datei bei Abweichungen auswerten;
8. erst dann Build 118 als **hardwarevalidiert** kennzeichnen.

## Distribution

- Pi: GitHub Release/Artifact des Universal-Image-Workflows
- Android: `GrowCentral-Nexus-Android-APK`
- iOS: `GrowCentral-Nexus-iOS-Sideload-IPA` (unsigned Ausgangspaket zur gerätebezogenen Signierung)
- Cloud: `scripts/install-135ercloud-v6.sh`
- APT Setup: `scripts/setup-135ercloud-apt-repo-v1.sh`
- APT Repository: `https://repo.dezender.de/apt`
- Public Project Console: `https://dezender.de`

## Design

Alle Oberflächen und Präsentationsassets folgen verbindlich dem **GrowCentral Nexus UI**. Logo und Branding bleiben unverändert. Details: [`docs/DESIGN_SYSTEM_NEXUS.md`](docs/DESIGN_SYSTEM_NEXUS.md).
