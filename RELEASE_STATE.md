# 135er-Grow Central · Canonical Release State

- **Stand:** 16. Oktober 2026
- **Repository-Version:** `alpha-0.7.5`
- **Branch:** `master`
- **Aktueller Raspberry-Pi-Hardwaretest-Candidate:** **Build 431**
- **Candidate-Tag:** `pi-universal-alpha-0.7.5-431`
- **Candidate-Commit:** `b51c19109db669832a2e009b239cc358fcd12428`
- **Status:** `CANDIDATE` – automatisierte Image-Gates bestanden; vollständige reale Prüfung dieses Images offen
- **Entwicklungsmodus:** `OPEN SOURCE` – öffentliches Repository und veröffentlichbare Artefakte

> Diese Datei ist die kanonische Referenz für README, Dokumentation, Pi-Image, Mobile, Cloud/APT und Release-Kommunikation. Historische Build-Dateien definieren nicht den aktuellen Candidate.

## Aktueller Candidate: Build 431

| Merkmal | Wert |
|---|---|
| Image | `135er_Grow_Central_RPi3Plus_Universal_alpha-0.7.5-build-431.img.xz` |
| Gr??e | 1.179.289.124 Byte |
| SHA-256 | `1095a6a9f66b8d67ce2536d20b32215c016d7d6654a0765a937cf949b6a3cf9b` |
| Quellstand | `b51c19109db669832a2e009b239cc358fcd12428` |
| Basis | Raspberry Pi OS Lite 64-bit, Universal-Image |
| Sensor-Firmware | `0.5.2` |
| Veröffentlichung | 16. Oktober 2026 |
| Hardwarestatus | `CANDIDATE`; dieses vollständige Image noch nicht real validiert |

[Release und Downloads](https://github.com/jygnw29kms-bit/135er-Grow-Central/releases/tag/pi-universal-alpha-0.7.5-431). Firmware-Build, Userspace-Boot/Reboot, Pristine-Prüfung, Komprimierung und Veröffentlichung bestanden. Die veröffentlichte Image-Prüfsumme stimmt mit dem GitHub-Asset-Digest überein. Begleitpakete wurden auf SHA256, ZIP-Integrität, Quellstand und Firmwaremanifest geprüft.

Build 431 enthält den aktuellen USB-Sensorpfad, individuelle MQTT-TLS-Zugänge, Zertifikatskompatibilität, vollständige CA-Übertragung, Sensor-Firmware 0.5.2, HomeKit-Integration sowie die aktuellen Diagnose- und Bodenfeuchtefunktionen.

Der reale Pi-4-Sensortest vom 14. Oktober bleibt als historischer Hardwarebefund dokumentiert. Seine Erkenntnisse sind in den aktuellen Quellstand eingeflossen; separate Build-369-Hotfix-Installer geh?ren nicht mehr zum aktiven Produktpfad. [Hardwarebefund](docs/de/SENSOR_HARDWARE_TEST_2026-10-14.md), [Kalibrierung](docs/de/SOIL_SENSOR_GUIDE.md).

Der `master`-Branch kann neuere Quellcode?nderungen als Build 431 enthalten. Ein neuer Image-Candidate wird erst durch den vollst?ndigen Image-Workflow erzeugt und erh?lt einen eigenen reproduzierbaren Quellstand.

## Verbindliche Hardwarestrategie

Grow Central verwendet ein Universal-Image.

| Hardware | Klasse | Produktstatus |
|---|---|---|
| Raspberry Pi 3B / 3B+ | `LEGACY_LITE` | unterstützt mit konservativen Ressourcenlimits |
| Raspberry Pi 4B / 400 / CM4 | `FULL_SUPPORT` | empfohlene Standardplattform |
| Raspberry Pi 5 / CM5 | `FULL_SUPPORT` Performance | Plattform mit zusätzlicher Leistungsreserve |

- Pi 3B/3B+ bleibt unterstützt, begrenzt aber nicht die Entwicklung neuer Full-Support-Funktionen.
- Separate Images entstehen nur, wenn unterschiedliche Kernel-, Paket- oder Servicebasen technisch zwingend werden.
- Runtime, Diagnose und Tests verwenden die zentrale Hardwareklassifikation.

## Release-Gates

Ein Build wird erst nach erfolgreichem Durchlauf der automatisierten Prüfungen zum `CANDIDATE`. Dazu gehören Quelltests, Sicherheitsprüfungen, Image-Anpassung, Boot, Reboot, Pristine-Prüfung, Komprimierung, Prüfsumme und Veröffentlichung.

`VALIDATED` wird ausschließlich nach dokumentierten Tests auf realer Zielhardware vergeben. Die Hardwareklassen werden getrennt bewertet:

- Raspberry Pi 3B/3B+ – Legacy/Lite;
- Raspberry Pi 4/400/CM4 – Full Support;
- Raspberry Pi 5/CM5 – Full Support Performance.

## Aktueller Testfokus

1. First Boot und sichere Vergabe eigener Zugangsdaten.
2. Setup-AP, WLAN-Übernahme und Rückfallverhalten bei Fehlkonfiguration.
3. Erreichbarkeit im Heimnetz und Persistenz nach Neustart.
4. Desktop- und Mobile-Oberfläche einschließlich iOS-WebKit-Verhalten.
5. Geräte-, Kamera-, Sensor- und Automationspfade.
6. Optionale Cloud-Verbindung ohne Abhängigkeit der lokalen Kernfunktionen.
7. Ressourcen- und Stabilitätstests getrennt nach Hardwareklasse.

## Distribution und Open Source

- Grow Central wird vollständig als Open-Source-Projekt entwickelt; das öffentliche Repository ist die zentrale Quellreferenz.
- Veröffentlichbare Images, App-Pakete, Installationsskripte und technische Dokumentation dürfen über die Projektkanäle bereitgestellt werden.
- Die öffentliche Produktseite unter `https://grow-central.de/` dient als Einstiegspunkt und kann auf Repository, Dokumentation und Releases verweisen.
- Zugangsdaten, Tokens, Schlüssel, private Zertifikate, lokale Diagnosepakete mit personenbezogenen Daten und sonstige Geheimnisse dürfen niemals in Commits oder Release-Artefakten enthalten sein.
- Für Drittanbieter-Komponenten gelten zusätzlich deren jeweilige Lizenz- und Markenbedingungen.

## Projekttrennung

Projektfremde Anwendungen sind keine funktionalen Bestandteile von Grow Central und werden nicht mehr in diesem Repository oder dessen CI-Pipelines mitgef?hrt.

## Validierung des aktuellen Kandidaten

- 321 Python-Tests, Firmware-Build, Sicherheits-/Projektgrenzen-/Domain-/Release-Prüfungen bestanden im geprüften Sensorstand.
- Home-Assistant-Komponente in CI gegen HA 2025.1.4 und 2026.10.1 geprüft; reale Sprachassistentenprüfung offen.
- Pi-4-Sensortest mit Hotfixes bestätigt; vollständiger Realtest von Build 431, Neustart-/Dauerbetrieb, Kalibrierung und andere Pi-Klassen offen.
- Status bleibt `CANDIDATE`.
