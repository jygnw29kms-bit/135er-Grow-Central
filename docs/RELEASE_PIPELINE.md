# Release-Pipeline – 135er-Grow Central

**Stand:** 2026-08-29  
**Kanonische Quellen:** [`../RELEASE_STATE.md`](../RELEASE_STATE.md), [`HARDWARE_SUPPORT_POLICY.md`](HARDWARE_SUPPORT_POLICY.md)

## Grundsatz

Es wird strikt zwischen folgenden Zuständen unterschieden:

1. **Repository-Stand** – aktueller `master`.
2. **Build/Artefakt** – durch GitHub Actions erzeugtes Paket.
3. **Published Candidate** – veröffentlichtes Universal-Image für den nächsten Realtest.
4. **Supportklassen-Validierung** – reale Prüfung getrennt nach Legacy/Lite und Full Support.
5. **Validated** – nur für tatsächlich real geprüfte Supportklassen.

Eine Commit-, Run- oder Buildnummer ist nicht automatisch hardwarevalidiert.

## Hardwarestrategie als Release-Gate

- ein **Universal-Image** bleibt Standard;
- Pi 3B/3B+ = `LEGACY_LITE`;
- Pi 4/400/CM4 = `FULL_SUPPORT` Standard;
- Pi 5/CM5 = `FULL_SUPPORT` Performance;
- Runtime-Komponenten verwenden die zentrale Klassifikation `shared/hardware_profile.py`;
- CI testet die Klassifikation;
- reale Tests werden pro Supportklasse dokumentiert;
- ein Pi-3-spezifischer Legacy/Lite-Fehler blockiert nicht automatisch die Full-Support-Freigabe für Pi 4/5, muss aber offen dokumentiert werden.

## Aktueller Stand

- Version: `alpha-0.7.5`
- letzter veröffentlichter Candidate: **Build 176** / `pi-universal-alpha-0.7.5-176`
- Build 176: `CANDIDATE`, noch nicht hardwarevalidiert
- aktueller `master`: enthält Post-176-Hardwareprofil-Runtime
- Konsequenz: **neuer Universal-Image-Build erforderlich**; erst dessen erfolgreicher Release wird neuer Candidate

## Verbindliche Release-Gates

1. Quellstand auf `master` konsistent halten.
2. Python-, Security-, Hardwareprofil-, Integrations- und Release-Guards ausführen.
3. Universal-Image aus exakt diesem Runtime-Stand bauen.
4. Boot/Reboot/Pristine/Packaging/Checksum/Release erfolgreich.
5. neuen Build als `CANDIDATE` veröffentlichen.
6. Realtest mindestens auf der Full-Support-Referenzklasse Pi 4/400 durchführen.
7. Pi-3-Legacy/Lite separat prüfen und Abweichungen separat klassifizieren.
8. Pi 5/Performance separat validieren, sofern Zielhardware verfügbar.
9. First Boot, Netzwerk, mDNS, GUI/Auth/Persistenz, Kiosk, Kamera, Cloud und Diagnose prüfen.
10. Website, README und kanonische Doku auf exakt denselben Stand synchronisieren.
11. `VALIDATED` nur für real bestätigte Supportklassen vergeben.

## Distribution

### Raspberry Pi

Workflow: `.github/workflows/build-pi3-image.yml` (historischer Dateiname; Output ist das Universal-Image).

Der Workflow erzeugt ein gemeinsames Image für alle Supportklassen. Separate Images dürfen nicht ohne dokumentierten technischen Grund eingeführt werden.

### Mobile

Android und iOS bleiben WebGUI-Clients; Hardwareklassifikation und Geräteautorität liegen beim Pi.

### Cloud / APT

Cloud V7 bleibt optional. Plesk-/Standalone-Varianten, Entitlements und APT-Upgrades sind unabhängig von der lokalen Hardwareklasse; die Pi-Seite kann ihre effektiven Fähigkeiten und Hardwareprofile an Diagnose-/Supportpfade melden.

### Website

`https://dezender.de/GC/` muss immer dieselbe Hardwarestrategie und denselben Candidate-Status wie `RELEASE_STATE.md` kommunizieren.

## Historische Dokumente

Build-spezifische Altdateien bleiben als Historie erhalten. Sie definieren weder aktuelle Hardwareklassen noch den aktuellen Candidate.
