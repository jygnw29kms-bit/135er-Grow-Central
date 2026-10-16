# 135er-Grow Central · Canonical Release State

- **Stand:** 14. Oktober 2026
- **Repository-Version:** `alpha-0.7.5`
- **Branch:** `master`
- **Aktueller Raspberry-Pi-Hardwaretest-Candidate:** **Build 375**
- **Candidate-Tag:** `pi-universal-alpha-0.7.5-375`
- **Candidate-Commit:** `f3837eb86028654becec96cd94488ba4d6a5e0cb`
- **Status:** `CANDIDATE` – automatisierte Image-Gates bestanden; vollständige reale Prüfung dieses Images offen
- **Entwicklungsmodus:** `OPEN SOURCE` – öffentliches Repository und veröffentlichbare Artefakte

> Diese Datei ist die kanonische Referenz für README, Dokumentation, Pi-Image, Mobile, Cloud/APT und Release-Kommunikation. Historische Build-Dateien definieren nicht den aktuellen Candidate.

## Aktueller Candidate: Build 375

| Merkmal | Wert |
|---|---|
| Image | `135er_Grow_Central_RPi3Plus_Universal_alpha-0.7.5-build-375.img.xz` |
| Größe | 1.164.234.740 Byte |
| SHA-256 | `e7712591867c81f6b0667cc81f59a46f465a95917b8de851ca879b29cde93b8e` |
| Quellstand | `f3837eb86028654becec96cd94488ba4d6a5e0cb` |
| Basis | Raspberry Pi OS Lite 64-bit, Universal-Image |
| Sensor-Firmware | `0.4.1` |
| Veröffentlichung | 14. Oktober 2026 |
| Hardwarestatus | `CANDIDATE`; dieses vollständige Image noch nicht real validiert |

[Release und Downloads](https://github.com/jygnw29kms-bit/135er-Grow-Central/releases/tag/pi-universal-alpha-0.7.5-375). Firmware-Build, Userspace-Boot/Reboot, Pristine-Prüfung, Komprimierung und Veröffentlichung bestanden. Die veröffentlichte Image-Prüfsumme stimmt mit dem GitHub-Asset-Digest überein. Begleitpakete wurden auf SHA256, ZIP-Integrität, Quellstand und Firmwaremanifest geprüft.

Build 375 enthält Mosquitto-Konfigurationskorrektur, USB-Sensoraufnahme, individuelle MQTT-TLS-Zugänge und Zertifikatskompatibilität, paketweisen CA-Transfer mit Längenprüfung, Firmwarediagnose 0.4.1, Supportdownload-Korrekturen und Bodenfeuchte-Historie. Der zusätzlich eingegangene Menüeditor ist ein lokaler Layoutentwurf; eine produktive Navigationsintegration wird nicht behauptet.

Der reale Pi-4-Teiltest wurde zuvor auf **Build 369 mit Hotfixes** durchgeführt: Sensoraufnahme, MQTT-Verbindung und Bodenfeuchte-Anzeige sind bestätigt. Diese Erkenntnisse fließen in Build 375 ein, ersetzen aber keinen vollständigen Realtest dieses Images. [Hardwarebefund](docs/de/SENSOR_HARDWARE_TEST_2026-10-14.md), [Kalibrierung](docs/de/SOIL_SENSOR_GUIDE.md).

Das Original-Image 369 bleibt unverändert und enthält Firmware 0.4.0. Bestehende funktionierende Installationen müssen nicht neu geflasht werden; dokumentierte In-place-Updates sind verfügbar. Der Git-Branch kann spätere Dokumentationsänderungen enthalten, während der Image-Quellstand exakt festgehalten bleibt.

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
- Pi-4-Sensortest mit Hotfixes bestätigt; vollständiger Realtest von Build 375, Neustart-/Dauerbetrieb, Kalibrierung und andere Pi-Klassen offen.
- Status bleibt `CANDIDATE`.
