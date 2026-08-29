# 135er-Grow Central · Canonical Release State

**Stand:** 2026-08-29  
**Repository-Version:** `alpha-0.7.5`  
**Branch:** `master`  
**Last published Raspberry-Pi hardware-test candidate:** **Build 176**  
**Published candidate tag:** `pi-universal-alpha-0.7.5-176`  
**Published candidate status:** `CANDIDATE` – noch nicht hardware-validiert  
**Current master:** enthält Post-176-Hardwareprofil-Runtime; neuer Universal-Image-Build erforderlich

> Diese Datei ist die kanonische Referenz für README, Website, Pi-Image, Mobile, Cloud/APT und Release-Dokumentation. Build 176 ist der letzte veröffentlichte Candidate. Seitdem enthält `master` Runtime-Änderungen für die verbindliche Hardware-Profilarchitektur; deshalb wird erst der nächste erfolgreiche Universal-Image-Build zum neuen Hardware-Testkandidaten.

## Verbindliche Hardwarestrategie

GrowCentral bleibt bei **einem Universal-Image**.

| Hardware | Klasse | Produktstatus |
|---|---|---|
| Raspberry Pi 3B / 3B+ | `LEGACY_LITE` | unterstützt mit konservativen Ressourcenlimits |
| Raspberry Pi 4B / 400 | `FULL_SUPPORT` | empfohlene Standardplattform |
| Raspberry Pi 5 | `FULL_SUPPORT` Performance | optimale Plattform |
| Compute Module 4 / 5 | `FULL_SUPPORT` | entsprechend der Generation |

- Pi 3B/3B+ bleibt unterstützt, darf aber neue Full-Support-Funktionen nicht auf sein Leistungsniveau begrenzen.
- Pi 4/400/5 definieren die Feature-Baseline für neue Funktionen.
- Separate Images entstehen nur, wenn unterschiedliche Kernel-, Paket- oder Servicebasen technisch zwingend werden.
- Runtime-Komponenten müssen die zentrale Klassifikation aus `shared/hardware_profile.py` verwenden.
- Diagnose und Support müssen Modell und aktives Hardwareprofil ausweisen.
- Verbindliche Details: [`docs/HARDWARE_SUPPORT_POLICY.md`](docs/HARDWARE_SUPPORT_POLICY.md).

## Letzter veröffentlichter Candidate: Build 176

- **Image:** `135er_Grow_Central_RPi3Plus_Universal_alpha-0.7.5-build-176.img.xz`
- **Größe:** ca. 1,49 GB
- **SHA-256:** `65047be1375461d5107c97527e90f6e6e458c3a61057175f15ec45752e450815`
- **Release:** `pi-universal-alpha-0.7.5-176`
- **Status:** Prerelease / `CANDIDATE`

Build 176 bleibt als veröffentlichtes Testartefakt verfügbar, ist aber nach Einführung der Hardware-Profil-Runtime nicht mehr identisch mit dem aktuellen `master`.

## Post-176 Runtime auf master

Die neue Hardwarearchitektur ist fester Bestandteil der Runtime:

- zentrale Modellklassifikation über `/proc/device-tree/model`;
- `LEGACY_LITE` für Pi 3B/3B+;
- Full-Support-Standardprofil für Pi 4/400/CM4;
- Full-Support-Performanceprofil für Pi 5/CM5;
- konservativer `UNCLASSIFIED`-Fallback;
- Hardwareprofil in der Diagnose-API;
- CI-Tests für alle Supportklassen;
- verbindliche Produkt-/Test-/Release-Dokumentation.

Damit ist ein neuer Image-Build erforderlich, bevor ein neuer Candidate benannt wird.

## Ressourcenprofile

### Pi 3B / 3B+ – Legacy/Lite

- Kamera konservativ bis 720p und reduzierte FPS;
- reduzierte Kiosk-Effekte;
- kompaktere Diagnosehistorie;
- konservative Worker-/Parallelitätsdefaults;
- lokale Kernfunktionen, Automationen, Smart-Home-Pfade und Cloud-Link bleiben grundsätzlich unterstützt.

### Pi 4 / 400 / CM4 – Full Support

- volle Nexus UI;
- Full-Support-Kamera- und Kioskpfad;
- Standard-Worker und normale Diagnosehistorie;
- empfohlene Basis für neue Installationen.

### Pi 5 / CM5 – Full Support Performance

- volle Nexus UI;
- Performance-Worker;
- erweiterte Diagnosehistorie;
- bevorzugt für zukünftige rechenintensive Funktionen.

## Cloud V7

Cloud V7 bleibt integriert: Plesk-/Standalone-Routing, Geräte-/Kunden-/Gruppenverwaltung, Status/Plan/Validität, Feature-Entitlements, sicherer Pi-Abruf, APT-Packaging und zentrale Diagnosepfade.

## Nächster Release-Schritt

1. CI für Hardwareprofil-Runtime vollständig grün.
2. neuen Universal-Image-Build erzeugen.
3. diesen neuen Build als nächsten `CANDIDATE` veröffentlichen.
4. reale Tests getrennt nach Supportklasse durchführen:
   - Pi 3B/3B+ Legacy/Lite;
   - Pi 4/400 Full Support;
   - Pi 5 Full Support Performance, sofern verfügbar.
5. First Boot, Heimnetzübernahme, GUI/Auth/Persistenz, mDNS, Kiosk, Kamera, Cloud und Diagnose prüfen.
6. erst nach realer Hardwarevalidierung den jeweiligen Supportpfad als `VALIDATED` markieren.

Ein Pi-3-spezifischer Legacy/Lite-Fehler blockiert nicht automatisch den Full-Support-Pfad für Pi 4/5; er muss jedoch transparent dokumentiert und als Legacy/Lite-Regression bewertet werden.

## Distribution

- letzter veröffentlichter Pi Candidate: `pi-universal-alpha-0.7.5-176`
- Android: GrowCentral Nexus Android APK
- iOS: GrowCentral Nexus iOS Sideload IPA
- APT Repository: `https://repo.dezender.de/apt`
- Public Project Console: `https://dezender.de/GC/`

## Projekttrennung

Ete’s Autoservice gehört nicht zum GrowCentral-Produkt. Eine technische Nutzung desselben Deployment-Kanals macht Ete’s-Inhalte nicht zu GrowCentral-Funktionen oder Projektmeilensteinen.

## Design

Alle Oberflächen und Präsentationsassets folgen dem **GrowCentral Nexus UI**. Logo und Branding bleiben unverändert.
