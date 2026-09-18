# Build 118 · Consolidated Release Notes

**Version:** `alpha-0.7.5`  
**Candidate tag:** `pi-universal-alpha-0.7.5-118`  
**Consolidated master anchor:** `e339602476f3a716ae28abd5334cb6f96447a646`  
**Status:** `CANDIDATE` – next hardware test, not yet validated

## Einordnung

Build 117 war der vorherige erfolgreich getestete Image-Stand. Durch die danach zusammengeführten Änderungen ist er für den nächsten Test überholt. Build 118 ist der konsolidierte Kandidat.

## Neu / zusammengeführt

### Kamera / Logitech C920

- firmware-/modell-/USB-ID-bewusste LED-Fähigkeitserkennung;
- LED-Controls werden nur exponiert, wenn die Kamera/Firmware sie tatsächlich unterstützt;
- bedingte V4L2-/Logitech-Steuerung statt blindem Schreiben;
- Tests für Capability Detection und LED-Steuersemantik;
- bestehende UVC-, Snapshot-, MJPEG- und V4L2-Control-Pfade bleiben erhalten.

### Display / Kiosk

- Elecrow 7-Zoll Touch-Kiosk;
- eigener systemd-Service;
- gehärtete ausführbare Dateirechte;
- lokale Grow-Central-GUI als Touch-Oberfläche.

### GUI / Plattform

- GrowCentral Nexus UI als verbindliche Designfamilie;
- Räume, Pflanzen, Growtagebuch und Automationen;
- System-/Netzwerk-/Build-/Diagnoseansichten;
- FRITZ! Smart Home und Tapo bleiben in der gemeinsamen lokalen Gerätearchitektur;
- Energie-/Kostenlogik und persistente Gerätezustände bleiben integriert.

### Mobile

Nexus Mobile wurde für den konsolidierten Plattformstand auf `0.2.1` angehoben:

- Android APK;
- iOS unsigned Sideload IPA;
- SHA-256-Prüfsummen;
- Local-Network-Nutzungstext auf iOS;
- Remote-Ziele nur via HTTPS.

### Cloud / APT / Website

- Cloud Server Installer V6 bleibt kanonischer Serverpfad;
- APT Bootstrap bleibt auf dem signierten Repository `https://repo.grow-central.de/apt`;
- grow-central.de zeigt Build 118 ausdrücklich als `CANDIDATE`;
- Website-Deploy publiziert Cloud-/APT-Installer gemeinsam mit Release-State und SHA-256-Summen.

## Hardwaretest-Checkliste

- [ ] frischer Boot
- [ ] Reboot
- [ ] First Boot / Setup AP / DHCP / DNS
- [ ] LAN/WLAN/mDNS
- [ ] GUI / Login / Persistenz
- [ ] C920-Erkennung
- [ ] Snapshot / MJPEG / V4L2
- [ ] LED-Capability Detection
- [ ] LED-Steuerung nur bei echter Unterstützung
- [ ] Elecrow 7-Zoll Kiosk, falls angeschlossen
- [ ] FRITZ!/Tapo, soweit verfügbar
- [ ] Mars-Hydro-/BLE-Diagnosepfad, soweit relevant
- [ ] Support Bundle bei Abweichungen

## Freigaberegel

Erst wenn die relevanten Punkte auf realer Hardware bestanden sind, darf Build 118 in `RELEASE_STATE.md`, Website und README von `CANDIDATE` auf `VALIDATED` wechseln.
