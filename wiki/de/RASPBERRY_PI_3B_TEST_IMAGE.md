# Raspberry Pi Test-Image · Build 118

**Version:** `alpha-0.7.5`  
**Master-Anker:** `e339602`  
**Kandidat:** **Build 118**  
**Tag:** `pi-universal-alpha-0.7.5-118`  
**Status:** `CANDIDATE` – noch nicht hardwarevalidiert

Build 117 wurde erfolgreich getestet, ist durch den konsolidierten e339-Stand jedoch überholt. Für den nächsten Hardwaretest ist Build 118 vorgesehen.

## Image-Basis

Der GitHub-Actions-Workflow `.github/workflows/build-pi3-image.yml` erzeugt ein universelles Raspberry-Pi-Image auf Raspberry Pi OS Lite 64-bit / Debian 13 (trixie). Die Buildnummer wird als BUILD-Metadatum in das Image geschrieben.

## Im Kandidaten enthalten

- Grow Central unter `/opt/135er-grow-central`;
- Python-Venv und Projektabhängigkeiten;
- First Boot / Setup AP / NetworkManager / mDNS;
- Bluetooth / BlueZ;
- lokale GrowCentral Nexus GUI;
- FRITZ! Smart Home und Tapo-Pfade;
- Logitech C920/UVC, Snapshot, MJPEG und dynamische V4L2-Regler;
- firmware-/modell-/USB-ID-bewusste Kamera-LED-Fähigkeitserkennung;
- bedingte LED-Steuerung nur bei erkannter Unterstützung;
- Elecrow 7-Zoll Touch-Kiosk mit systemd-Service;
- Support-/Diagnosepfade;
- SSH, Firewall-/Hardening- und Update-Grundlagen.

## Zugriff

```text
First Boot: http://10.42.0.1/
Nach Setup: http://135er-Grow-Central.local/
Kompatibilität: http://135er-Grow-Central.local:8080/
```

Temporäre Image-Testzugänge dürfen ausschließlich für die Ersteinrichtung/Tests verwendet und im First Boot ersetzt werden.

## Sichere Defaults

```text
DF100M_ALLOW_WRITES=false
GC_REMOTE_COMMANDS=false
GC_CLOUD_ENABLED=false
```

Unbestätigte Mars-Hydro-/BLE-Schreibpfade bleiben deny-by-default.

## Build-118-Testablauf

1. exakt Build 118 flashen;
2. frischen Boot prüfen;
3. Setup AP / DHCP / DNS prüfen;
4. LAN/WLAN und mDNS prüfen;
5. First Boot abschließen und GUI öffnen;
6. Reboot durchführen;
7. Persistenz von Setup, Geräten und Einstellungen prüfen;
8. C920 erkennen und Snapshot/MJPEG/V4L2 testen;
9. Kamera-LED-Fähigkeitserkennung prüfen;
10. LED nur dann schalten, wenn die konkrete Kamera/Firmware Unterstützung meldet;
11. Elecrow-Kiosk prüfen, sofern angeschlossen;
12. FRITZ!/Tapo-Pfade prüfen, sofern Hardware vorhanden;
13. Mars-Hydro-/BLE-Diagnose ohne unbestätigte Writes prüfen;
14. bei jeder Abweichung `Grow-Central-Support-latest.tar.gz` erzeugen.

## Release-Regel

Build 118 bleibt `CANDIDATE`, bis der reale Hardwaretest bestanden ist. Ein neuer Build >118 wird nicht nur wegen Dokumentations-/Website-/Mobile-Änderungen erzeugt; er ist erst bei einem tatsächlichen Laufzeitfix erforderlich.

Kanonisch: [Release State](../../RELEASE_STATE.md) · [Build 118 Notes](../../docs/RELEASE_NOTES_BUILD_118.md) · [Release Pipeline](../../docs/RELEASE_PIPELINE.md)
