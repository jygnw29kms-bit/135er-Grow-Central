# 135er-Grow Central · Canonical Release State

**Stand:** 2026-08-29  
**Repository-Version:** `alpha-0.7.5`  
**Branch:** `master`  
**Current clean master:** `9700dee29fe7c4904e0fea115a38ce1f678ac3c7`  
**Current Raspberry-Pi hardware-test candidate:** **Build 176**  
**Candidate tag:** `pi-universal-alpha-0.7.5-176`  
**Status:** `CANDIDATE` – noch nicht hardware-validiert

> Diese Datei ist die kanonische Referenz für README, Website, Pi-Image, Mobile, Cloud/APT und Release-Dokumentation. Ein erfolgreicher CI-/Image-Build bestätigt den technischen Build, ersetzt aber nicht den realen Hardwaretest. Erst nach bestandener Prüfung auf echter Zielhardware darf `VALIDATED` gesetzt werden.

## Aktueller Stand

- **Pi Image:** Build 176, Universal Image für Raspberry Pi 3B/3B+, 4B/400, 5 und kompatible Compute Modules.
- **Image-Datei:** `135er_Grow_Central_RPi3Plus_Universal_alpha-0.7.5-build-176.img.xz`
- **Image-Größe:** ca. 1,49 GB.
- **Image SHA-256:** `65047be1375461d5107c97527e90f6e6e458c3a61057175f15ec45752e450815`
- **Release:** `pi-universal-alpha-0.7.5-176` · Prerelease/CANDIDATE.
- **Master:** `9700dee2` – Diagnose trennt Setup-AP sauber von First-Boot-Abschlussmarkern.
- **Cloud:** V7 ist auf `master` integriert.
- **Servervarianten:** Plesk-Integration und Standalone-Webinterface sind vorgesehen.
- **APT:** Cloud-Komponenten bleiben auf bestehenden Instanzen über den normalen APT-Upgradepfad aktualisierbar.
- **Freischaltungen:** V7 verwaltet Geräte-/Kunden-Zuordnung, Gruppen, Status, Pläne und einzelne Feature-Entitlements.
- **Pi ↔ Cloud:** Pis können ihre effektiven V7-Entitlements sicher abrufen.

## Seit Build 159 hinzugekommene Schwerpunkte

- First-Boot-/Captive-Portal-Härtungen und robustere Heimnetzübernahme;
- zuverlässigere lokale Health-Probes nach Netzwerkwechseln;
- mDNS-Fix gegen Reverse-Record-Konflikte mit dem nativen Hostnamen;
- Display-/Kiosk-Härtungen inklusive erneuter `tty1`-Übernahme beim Start;
- touch-taugliche Kiosk-/Keyboard-Response-Verarbeitung;
- deaktiviertes veraltetes Kiosk-Asset-Caching;
- klarere Cloud-Statusanzeige zwischen lokalem Cloud-Link und Remote-Konnektivität;
- Kamera-720p-Policy wird auch bei direktem Modulimport installiert;
- Diagnose trennt laufenden Setup-AP von echten First-Boot-Abschlussmarkern.

## Cloud V7

Aktuell integriert sind unter anderem:

- V7 Admin- und Entitlement-Endpunkte;
- Routing für Plesk und Standalone-Betrieb;
- Geräteverwaltung mit manueller Freischaltung;
- Kunden- und Gerätegruppen;
- Status/Plan/Validität/Notizen;
- Feature-Entitlements für `remote_control`, `camera`, `history_extended`, `alerts`, `automation_pro`, `api_access` und `beta_features`;
- sicherer Pi-Abruf der effektiven Freischaltungen;
- APT-Packaging und CI-Validierung der V7-Pfade;
- statisches SQL-Update der Entitlements als Security-Härtung;
- zentrale Diagnose-/Cloud-Pfade mit gehärteten Upload- und Proxy-Grenzen.

## Hardware-Test Build 176

Der nächste reale Test läuft in dieser Reihenfolge:

1. Build-176-Image frisch flashen.
2. Setup-AP / First Boot öffnen.
3. First-Boot-Assistent vollständig durchführen.
4. Heim-WLAN konfigurieren.
5. Reboot durchführen.
6. Prüfen, dass der Pi danach sauber im Heimnetz erscheint.
7. GUI/Login/Persistenz prüfen.
8. Display/Kiosk und Touch prüfen.
9. Kamera/C920 inkl. 720p-Policy prüfen.
10. mDNS/Hostname und lokale Erreichbarkeit prüfen.
11. Cloud-Anbindung und Diagnose des Pi prüfen.
12. Erst danach Server/Plesk-Integration und Entitlements testen.

### Akzeptanz für die erste Teststufe

- Setup-AP und DHCP funktionieren ohne manuelle Reparatur.
- First-Boot-GUI ist erreichbar.
- WLAN-Konfiguration wird gespeichert.
- Reboot funktioniert.
- Pi kommt danach zuverlässig im Heimnetz hoch.
- lokale GUI ist erreichbar und Login/Persistenz funktionieren.
- Kiosk/Display kommt zuverlässig hoch.
- `135er-GrowCentral.local` ist im Zielnetz nachvollziehbar erreichbar.
- Cloud-Verbindung liefert einen nachvollziehbaren Gerätestatus.
- Diagnose meldet Setup-AP und Abschlussstatus korrekt getrennt.

## Release-Gates Build 176

1. CI-/Security-/Integrationsprüfungen erfolgreich;
2. exakt Build 176 testen;
3. First Boot erfolgreich;
4. Heimnetzübernahme + Reboot erfolgreich;
5. lokale GUI + Auth + Persistenz erfolgreich;
6. Kiosk/Display/Touch erfolgreich;
7. Kamera/C920 erfolgreich;
8. mDNS/Hostname erfolgreich;
9. Cloud-Verbindung + Diagnose erfolgreich;
10. Plesk-/Standalone-Cloud-V7-Verwaltung prüfen;
11. Entitlement/Freischaltung eines Test-Pi prüfen;
12. erst danach `CANDIDATE` → `VALIDATED`.

## Distribution

- Pi: `pi-universal-alpha-0.7.5-176`
- Image: `135er_Grow_Central_RPi3Plus_Universal_alpha-0.7.5-build-176.img.xz`
- SHA-256: `65047be1375461d5107c97527e90f6e6e458c3a61057175f15ec45752e450815`
- Android: GrowCentral Nexus Android APK
- iOS: GrowCentral Nexus iOS Sideload IPA
- APT Repository: `https://repo.dezender.de/apt`
- Public Project Console: `https://dezender.de/GC/`

## Projekttrennung

Ete’s Autoservice gehört nicht zum GrowCentral-Produkt. Das GrowCentral-Repository kann technisch als Deployment-Kanal verwendet werden; Ete’s-spezifische Inhalte und Deployments sind jedoch keine GrowCentral-Funktionen, Releases oder Projektmeilensteine.

## Design

Alle Oberflächen und Präsentationsassets folgen dem **GrowCentral Nexus UI**. Logo und Branding bleiben unverändert. Details: [`docs/DESIGN_SYSTEM_NEXUS.md`](docs/DESIGN_SYSTEM_NEXUS.md).
