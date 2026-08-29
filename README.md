<p align="center"><img src="docs/assets/brand/repository-banner-v0.9.png" alt="135er-Grow Central · GrowCentral Nexus UI" width="100%"></p>

<p align="center"><a href="#deutsch"><strong>Deutsch</strong></a> · <a href="#english"><strong>English</strong></a> · <a href="RELEASE_STATE.md"><strong>Release State</strong></a> · <a href="docs/HARDWARE_SUPPORT_POLICY.md"><strong>Hardware Policy</strong></a> · <a href="docs/HARDWARE_TEST_PLAN.md"><strong>Hardware Test</strong></a></p>

<p align="center">
<img alt="Version" src="https://img.shields.io/badge/version-alpha--0.7.5-71ff3b?style=flat-square&labelColor=061015">
<img alt="Published Pi Candidate" src="https://img.shields.io/badge/published%20candidate-Build%20176-ffb52b?style=flat-square&labelColor=061015">
<img alt="Image" src="https://img.shields.io/badge/image-Universal-35e8da?style=flat-square&labelColor=061015">
<img alt="Pi 3" src="https://img.shields.io/badge/Pi%203B%2F3B%2B-Legacy%2FLite-ffb52b?style=flat-square&labelColor=061015">
<img alt="Pi 4/5" src="https://img.shields.io/badge/Pi%204%2F5-Full%20Support-71ff3b?style=flat-square&labelColor=061015">
</p>

# Deutsch

**135er-Grow Central** ist eine Local-First Steuer-, Überwachungs- und Automationsplattform für Raspberry Pi mit optionaler eigener Cloud-Anbindung.

## Verbindliche Hardwarestrategie

GrowCentral verwendet weiterhin **ein Universal-Image**. Die Hardware wird zur Laufzeit zentral erkannt; Funktionen und Ressourcenprofile richten sich nach `shared/hardware_profile.py`.

| Hardware | Supportklasse | Rolle |
|---|---|---|
| Raspberry Pi 3B / 3B+ | **Legacy/Lite** | weiterhin unterstützt, konservative Ressourcenlimits |
| Raspberry Pi 4B / 400 | **Full Support** | empfohlene Standardplattform |
| Raspberry Pi 5 | **Full Support / Performance** | optimale Plattform für rechenintensive Funktionen |
| Compute Module 4 / 5 | **Full Support** | entsprechend der Generation |

**Minimum / Legacy:** Pi 3B/3B+  
**Empfohlen:** Pi 4 ab 2 GB  
**Optimal:** Pi 4 mit 4 GB oder Pi 5

Pi 3 bleibt unterstützt, darf aber neue Full-Support-Funktionen nicht mehr auf sein Leistungsniveau begrenzen. Separate Images entstehen erst, wenn unterschiedliche Kernel-, Paket- oder Servicebasen technisch zwingend werden. Details: [`docs/HARDWARE_SUPPORT_POLICY.md`](docs/HARDWARE_SUPPORT_POLICY.md).

## Release-Stand

Der letzte veröffentlichte Universal-Image-Candidate ist **Build 176** (`pi-universal-alpha-0.7.5-176`). Seit Build 176 enthält `master` zusätzliche Runtime-Änderungen für die neue Hardware-Profilarchitektur. Daher bleibt Build 176 der letzte veröffentlichte Candidate, ist aber nicht mehr runtime-identisch mit dem aktuellen `master`; der nächste erfolgreiche Image-Build wird der neue Hardware-Testkandidat.

Build 176 Image: `135er_Grow_Central_RPi3Plus_Universal_alpha-0.7.5-build-176.img.xz`  
SHA-256: `65047be1375461d5107c97527e90f6e6e458c3a61057175f15ec45752e450815`

## Hardware-Profilierung in der Runtime

Die zentrale Klassifikation ist Teil der Runtime und Diagnose. Komponenten sollen keine eigenen Modell-Sonderfälle pflegen. Aktuelle Profile:

- `LEGACY_LITE`: Pi 3B/3B+ – Kamera konservativ bis 720p/reduzierte FPS, reduzierte Kiosk-Effekte, kompaktere Diagnosehistorie, konservative Worker;
- `FULL_SUPPORT` Standard: Pi 4/400/CM4 – volle Nexus UI, normale Parallelität, Full-Support-Kamera-/Diagnoseprofil;
- `FULL_SUPPORT` Performance: Pi 5/CM5 – volle Nexus UI, Performance-Worker und erweiterte Diagnosehistorie;
- `UNCLASSIFIED`: unbekannte Hardware – konservativer Diagnosemodus ohne Supportzusage.

Die Diagnose-API weist Modell und aktives Hardwareprofil aus.

## Local First + Cloud V7

Der Raspberry Pi bleibt die autoritative lokale Instanz. Cloud V7 ergänzt den Betrieb mit Geräte-/Kunden-Zuordnung, Gruppen, Status/Plan, Feature-Entitlements, sicherem Pi-Abruf und APT-Upgradepfad. Lokale Kernfunktionen sollen auch ohne Cloud weiterarbeiten.

Lokale Bereiche umfassen First Boot/Netzwerk, GUI/Auth, Räume/Grow, Automationen, FRITZ! Smart Home, Tapo, Logitech C920/UVC, Mars-Hydro-/Bluetooth-Diagnose, Kiosk/Touch und Supportdiagnose.

## Tests und Release-Gates

CI prüft die Hardwareklassifikation mindestens für Pi 3B/3B+, Pi 4/400, Pi 5 sowie CM4/CM5. Reale Hardwarevalidierung wird nach Supportklasse dokumentiert. Ein Pi-3-spezifischer Legacy/Lite-Fehler darf nicht automatisch den Full-Support-Pfad für Pi 4/5 blockieren, muss aber sichtbar dokumentiert werden.

Ausführlich: [`docs/HARDWARE_TEST_PLAN.md`](docs/HARDWARE_TEST_PLAN.md).

## Zugriff

- First Boot: `http://10.42.0.1/`
- lokal nach Einrichtung: `http://135er-GrowCentral.local/`
- Port `8080`: Kompatibilitätspfad

## Mobile

Android APK und iOS Sideload IPA bleiben Clients der GrowCentral-WebGUI; die Geräteautorität bleibt beim Pi.

## Kanonische Dokumente

- [`RELEASE_STATE.md`](RELEASE_STATE.md)
- [`docs/HARDWARE_SUPPORT_POLICY.md`](docs/HARDWARE_SUPPORT_POLICY.md)
- [`docs/HARDWARE_TEST_PLAN.md`](docs/HARDWARE_TEST_PLAN.md)
- [`docs/DESIGN_SYSTEM_NEXUS.md`](docs/DESIGN_SYSTEM_NEXUS.md)
- [`SECURITY.md`](SECURITY.md)

---

# English

GrowCentral keeps **one universal Raspberry Pi image** and uses a central runtime hardware profile. Raspberry Pi 3B/3B+ remains supported as **Legacy/Lite**; Raspberry Pi 4/400 and 5 are **Full Support** and define the feature baseline for future development. Pi 3 limitations must not constrain new Full-Support features.

The last published candidate is Build 176. Current `master` contains post-176 hardware-profile runtime changes, so the next successful universal-image build will become the next hardware-test candidate.

Canonical policy: [`docs/HARDWARE_SUPPORT_POLICY.md`](docs/HARDWARE_SUPPORT_POLICY.md). Canonical release state: [`RELEASE_STATE.md`](RELEASE_STATE.md).
