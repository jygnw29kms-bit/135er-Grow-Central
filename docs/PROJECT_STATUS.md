# Project Status – 135er-Grow Central

**Stand:** 2026-08-29  
**Version:** `alpha-0.7.5`  
**Branch:** `master`  
**Letzter veröffentlichter Pi-Candidate:** Build 176  
**Aktueller master:** Post-176-Hardwareprofil-Runtime; neuer Universal-Image-Build erforderlich  
**Kanonische Quellen:** [`../RELEASE_STATE.md`](../RELEASE_STATE.md), [`HARDWARE_SUPPORT_POLICY.md`](HARDWARE_SUPPORT_POLICY.md)

## Verbindliche Hardwareklassen

- Pi 3B/3B+ → `LEGACY_LITE`, weiterhin unterstützt;
- Pi 4/400/CM4 → `FULL_SUPPORT` Standard, empfohlen;
- Pi 5/CM5 → `FULL_SUPPORT` Performance;
- ein Universal-Image bleibt Standard.

Pi 3 begrenzt neue Full-Support-Funktionen nicht mehr. Separate Images nur bei technisch zwingend unterschiedlichen Kernel-/Paket-/Servicebasen.

## Aktueller Funktionsstand

| Bereich | Status | Hardwarebezug |
|---|---|---|
| Local FastAPI / GUI | implemented | alle unterstützten Klassen |
| Hardwareprofil-Runtime | implemented + tests | zentrale Quelle `shared/hardware_profile.py` |
| Diagnose Hardwareprofil | implemented | Modell + Profil in Snapshot |
| First Boot / Setup AP | implemented | alle Klassen |
| LAN/WLAN / mDNS | implemented | alle Klassen |
| FRITZ! Smart Home | implemented baseline | alle Klassen |
| TP-Link Tapo | implemented baseline | alle Klassen |
| Räume/Grow/Automation | implemented baseline | alle Klassen |
| Logitech C920 / UVC | implemented | Pi 3 konservativ 720p; Pi 4/5 Full bis 1080p |
| Kiosk/Touch | implemented baseline | Pi 3 reduzierte Effekte; Pi 4/5 full |
| Diagnosehistorie | profile-aware baseline | compact / standard / extended |
| Workerprofil | profile-aware baseline | conservative / standard / performance |
| Cloud | V7 | optional, alle Klassen |
| Mobile | Nexus Client | unabhängig vom Pi-Modell |
| Website | public product site | Hardwareklassen veröffentlicht |

## Release-Lage

Build 176 bleibt letzter veröffentlichter `CANDIDATE`, ist aber nicht mehr runtime-identisch mit `master`. Die Hardwareprofil-Runtime ist eine echte Imageänderung; daher muss ein neuer Universal-Image-Build erfolgreich durchlaufen und anschließend als neuer Candidate benannt werden.

## Nächster Meilenstein

1. CI komplett grün.
2. neuen Universal-Image-Build veröffentlichen.
3. Hardwaretests getrennt nach Legacy/Lite und Full Support durchführen.
4. erst danach Supportklassen gezielt als `VALIDATED` markieren.
