# 135er-Grow Central · Canonical Release State

- **Stand:** 5. Oktober 2026
- **Repository-Version:** `alpha-0.7.5`
- **Branch:** `master`
- **Aktueller Raspberry-Pi-Hardwaretest-Candidate:** **Build 351**
- **Candidate-Tag:** `pi-universal-alpha-0.7.5-351`
- **Candidate-Commit:** `16e80b7c9836125f5ee4f8cdf48b92fd67054f60`
- **Status:** `CANDIDATE` – automatisierte Build-/Release-Gates bestanden, reale Hardwarevalidierung je Hardwareklasse weiterhin erforderlich
- **Entwicklungsmodus:** `OPEN SOURCE` – öffentliches Repository und öffentliche, veröffentlichbare Projektartefakte

> Diese Datei ist die kanonische Referenz für README, aktive Projektdokumentation, Pi-Image, Mobile, Cloud/APT und Release-Kommunikation. Historische Build-Dateien bleiben nachvollziehbar, definieren aber nicht den aktuellen Candidate.

## Aktueller Candidate: Build 351

| Merkmal | Wert |
|---|---|
| Image | `135er_Grow_Central_RPi3Plus_Universal_alpha-0.7.5-build-351.img.xz` |
| Größe | 1.158.228.444 Byte |
| SHA-256 | `7078c0aab4766ed9cfb7b69e4e00957099df2ef33f8a8dab0a6c4e88e0f18f6a` |
| Basis | Raspberry Pi OS Lite 64-bit |
| Architektur | dauerhaft headless, Local First |
| Veröffentlichung | 24. September 2026 |
| Hardwarestatus | `CANDIDATE`; reale Validierung je Hardwareklasse offen |

Build 351 ist der neueste veröffentlichte Universal-Image-Candidate. Er verwendet die zentrale Hardwareerkennung, die gehärtete Ersteinrichtung ohne bekannte Factory-Passwörter, die lokale Web-/Mobile-Oberfläche und den optionalen Cloud-Link. SSH bleibt standardmäßig deaktiviert und wird nur ausdrücklich eingerichtet.

Der `master`-Branch kann nach Build 351 bereits neuere Quellcodeänderungen enthalten. Ein neuer Quellstand wird deshalb erst dann als neuer Image-Candidate bezeichnet, wenn der vollständige Image-Workflow erfolgreich durchlaufen und ein entsprechender Release-Tag veröffentlicht wurde.

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

Ete’s Autoservice, Touran, God’s Eye und Dyson V11 BMS sind keine funktionalen Bestandteile von Grow Central. Falls sie vorübergehend dieselbe Repository- oder CI-Infrastruktur nutzen, müssen Builds, Deployments, Secrets, Releases und Dokumentation technisch getrennt bleiben.
