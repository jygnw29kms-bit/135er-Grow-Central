# 135er-Grow Central · Canonical Release State

- **Stand:** 2. September 2026
- **Repository-Version:** `alpha-0.7.5`
- **Branch:** `master`
- **Aktueller Raspberry-Pi-Hardwaretest-Candidate:** **Build 199**
- **Candidate-Tag:** `pi-universal-alpha-0.7.5-199`
- **Candidate-Commit:** `34442bc41d2c79328d3d5c61eb63a744f4c433a6`
- **Status:** `CANDIDATE` – automatisierte Gates bestanden, reale Hardwarevalidierung offen
- **Entwicklungsmodus:** `CLOSED` – keine öffentliche Distribution neuer Projektartefakte

> Diese Datei ist die kanonische Referenz für README, aktive Projektdokumentation, Pi-Image, Mobile, Cloud/APT und interne Release-Kommunikation. Historische Build-Dateien sind Nachweise vergangener Stände und definieren nicht den aktuellen Candidate.

## Aktueller Candidate: Build 199

| Merkmal | Wert |
|---|---|
| Image | `135er_Grow_Central_RPi3Plus_Universal_alpha-0.7.5-build-199.img.xz` |
| Größe | 1.159.817.996 Byte |
| SHA-256 | `cf1cdc65ada868573eddf0da6774203843f9f9e61c3a2a4ae3b68e8fc6b09d1b` |
| Basis | Raspberry Pi OS Lite 64-bit |
| Architektur | dauerhaft headless, Local First |
| Veröffentlichung | 31. August 2026 |
| Hardwarestatus | noch nicht `VALIDATED` |

Build 199 enthält den aktuellen headless Runtime-Stand, die zentrale Hardwareklassifikation, die überarbeitete Desktop-/Mobile-Oberfläche und die gehärtete Ersteinrichtung ohne bekannte Factory-Passwörter. SSH bleibt standardmäßig deaktiviert und wird nur ausdrücklich eingerichtet.

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

## Distribution und Vertraulichkeit

- Repository, neue Releases, Images, App-Pakete und Installationsskripte werden bis auf Weiteres geschlossen geführt.
- Die öffentliche Produktseite unter `https://dezender.de/GC/` enthält keine internen Downloads, Buildnummern, Commit-IDs, Protokollnamen oder Betriebsendpunkte.
- Bereits früher veröffentlichte Inhalte gelten als potenziell eingesehen oder kopiert und dürfen nicht als vertraulich vorausgesetzt werden.
- Für bereits unter MIT veröffentlichte Fassungen bleibt die vorhandene Lizenz maßgeblich; eine Neulizenzierung künftiger Fassungen wird separat geklärt.
- Zugangsdaten, Tokens, Schlüssel und Kundendaten dürfen niemals in Commits oder Release-Artefakten enthalten sein.

## Projekttrennung

Ete’s Autoservice ist kein Bestandteil von 135er-Grow Central. Gemeinsame Infrastruktur oder ein gemeinsamer Deployment-Kanal begründen keine funktionale oder kommerzielle Verbindung.
