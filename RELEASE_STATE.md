# 135er-Grow Central · Canonical Release State

**Stand:** 2026-08-23  
**Repository-Version:** `alpha-0.7.5`  
**Branch:** `master`  
**Build-118 Runtime-/Image-Anker:** `e339602476f3a716ae28abd5334cb6f96447a646`  
**Next Raspberry-Pi hardware-test candidate:** **Build 118**  
**Candidate tag:** `pi-universal-alpha-0.7.5-118`

> Diese Datei ist die kanonische Referenz für README, Website, Pi-Image, Mobile, Cloud/APT und Release-Dokumentation. `e339602` bezeichnet den Laufzeit-/Image-Stand des Build-118-Kandidaten; der `master`-Branch enthält danach zusätzlich Dokumentations-, Mobile-, Packaging- und Publishing-Commits. Historische Build-Dokumente dürfen ältere Nummern enthalten, müssen aber als Historie verstanden werden.

## Statusmodell

- **Build 117:** vorheriger erfolgreich getesteter Image-Stand; durch den zusammengeführten `e339`-Laufzeitstand funktional überholt.
- **Build 118:** aktueller Kandidat für den nächsten realen Hardwaretest. **Status: CANDIDATE.** Erst nach bestandenem Pi-Test darf der Status auf `VALIDATED` wechseln.
- **Stable:** weiterhin nicht freigegeben; Projekt bleibt `alpha-0.7.5`.

## In Build 118 zusammengeführt

- Raspberry-Pi Local-First GUI, First Boot, Netzwerk, FRITZ! und Tapo;
- Logitech-C920/UVC-Pfad;
- firmware-/modell-/USB-ID-bewusste Kamera-LED-Fähigkeitserkennung;
- bedingte V4L2-/Logitech-LED-Steuerung statt blindem Schreiben;
- Tests für LED-Fähigkeits- und Steuersemantik;
- Elecrow 7-Zoll Touch-Kiosk inklusive systemd-Service und gehärteten Dateirechten;
- Räume/Grow, Automationen, Diagnose und Supportpfade;
- der zu diesem Zeitpunkt integrierte GUI-/Runtime-Stand.

## Nach dem Runtime-Anker auf `master` synchronisiert

Diese Änderungen verändern den vorgesehenen Pi-Laufzeitkandidaten Build 118 nicht und erzeugen deshalb bewusst keinen künstlichen Build 119:

- GrowCentral Nexus UI als verbindliches Repo-/Produkt-Designsystem;
- README, Docs, Wiki und Projektgeschichte auf Build 118 konsolidiert;
- Nexus Mobile 0.2.1 für Android und iOS-Sideloading;
- dezender.de Nexus Project Console;
- Cloud-V6/APT-Release-Paket und SHA-256-Publishing;
- Release-Consistency-Guards.

## Release-Gates Build 118

1. automatisierte Python-/Security-/Integrationsprüfungen für den Runtime-Stand;
2. exakt das Build-118-Image verwenden;
3. Image booten und rebooten;
4. First Boot, LAN/WLAN/AP, GUI und Persistenz prüfen;
5. C920 inkl. LED-Fähigkeiten auf realer Hardware prüfen;
6. relevante FRITZ!/Tapo/Mars-Hydro-/Displaypfade prüfen;
7. Support-Datei bei Abweichungen auswerten;
8. erst danach Status von `CANDIDATE` auf `VALIDATED` setzen.

## Distribution

- Pi: GitHub Release/Artifact `pi-universal-alpha-0.7.5-118`
- Android: `GrowCentral-Nexus-Android-APK`
- iOS: `GrowCentral-Nexus-iOS-Sideload-IPA` (unsigned Ausgangspaket zur gerätebezogenen Signierung)
- Cloud: `scripts/install-135ercloud-v6.sh`
- APT Setup: `scripts/setup-135ercloud-apt-repo-v1.sh`
- APT Repository: `https://repo.dezender.de/apt`
- Public Project Console: `https://dezender.de`

## Design

Alle Oberflächen und Präsentationsassets folgen verbindlich dem **GrowCentral Nexus UI**. Logo und Branding bleiben unverändert. Details: [`docs/DESIGN_SYSTEM_NEXUS.md`](docs/DESIGN_SYSTEM_NEXUS.md).
