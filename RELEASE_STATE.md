# 135er-Grow Central · Canonical Release State

**Stand:** 2026-08-28  
**Repository-Version:** `alpha-0.7.5`  
**Branch:** `master`  
**Current clean master:** `2588886b951802741977cfc87d2e50552a3e6553`  
**Current Raspberry-Pi hardware-test candidate:** **Build 159**  
**Candidate tag:** `pi-universal-alpha-0.7.5-159`  
**Status:** `CANDIDATE` – noch nicht hardware-validiert

> Diese Datei ist die kanonische Referenz für README, Pi-Image, Mobile, Cloud/APT und Release-Dokumentation. Der reale Hardwaretest entscheidet über `VALIDATED`; ein erfolgreicher CI-Build allein reicht dafür nicht.

## Aktueller Stand

- **Pi Image:** Build 159, Universal Image für Raspberry Pi 3B/3B+, 4B/400, 5 und kompatible Compute Modules.
- **Image-Datei:** `135er_Grow_Central_RPi3Plus_Universal_alpha-0.7.5-build-159.img.xz`
- **Image SHA-256:** `136ebc324595ccf732b4e48292b3cbf6a09e362846c53f2070190c44a3953f3b`
- **Release:** `pi-universal-alpha-0.7.5-159` · Prerelease/CANDIDATE.
- **Cloud:** V7 ist auf `master` integriert.
- **Servervarianten:** Plesk-Integration und Standalone-Webinterface sind vorgesehen.
- **APT:** Cloud-Komponenten werden paketiert und sollen auf bestehenden Instanzen über den normalen APT-Upgradepfad aktualisierbar bleiben.
- **Freischaltungen:** V7 verwaltet Geräte-/Kunden-Zuordnung, Gruppen, Status, Pläne und einzelne Feature-Entitlements.
- **Pi ↔ Cloud:** Pis können ihre effektiven V7-Entitlements sicher abrufen.

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
- statisches SQL-Update der Entitlements als Security-Härtung.

## Aktueller Hardware-Test Build 159

Der nächste reale Test läuft in dieser Reihenfolge:

1. Build-159-Image frisch flashen.
2. Setup-AP / First Boot öffnen.
3. First-Boot-Assistent vollständig durchführen.
4. Heim-WLAN konfigurieren.
5. Reboot durchführen.
6. Prüfen, dass der Pi danach sauber im Heimnetz erscheint.
7. GUI/Login/Persistenz prüfen.
8. Cloud-Anbindung des Pi prüfen.
9. Erst danach den Server vorbereiten und das Plesk-Plugin installieren.

### Akzeptanz für die erste Teststufe

- Setup-AP und DHCP funktionieren ohne manuelle Reparatur.
- First-Boot-GUI ist erreichbar.
- WLAN-Konfiguration wird gespeichert.
- Reboot funktioniert.
- Pi kommt danach zuverlässig im Heimnetz hoch.
- lokale GUI ist erreichbar und Login/Persistenz funktionieren.
- Cloud-Verbindung ist technisch erreichbar und liefert einen nachvollziehbaren Gerätestatus.

## Plesk-Server vor Plugin-Installation

Vor Installation des Grow-Central-Plesk-Plugins wird das Hostsystem zuerst regulär aktualisiert:

```bash
sudo apt update
sudo apt upgrade
```

Danach prüfen:

```bash
sudo apt --fix-broken install
sudo systemctl --failed
```

Falls Kernel, libc, systemd oder andere zentrale Komponenten aktualisiert wurden, ist vor der Plugin-Installation ein geplanter Reboot sinnvoll. Anschließend Plesk-Funktion, Webserver, PHP/Proxy und Datenbank prüfen.

**Wichtig:** Das Grow-Central-Plugin erst installieren, wenn das Plesk-System nach dem Update wieder sauber läuft. So lassen sich Server-/Plesk-Probleme klar von Grow-Central-Problemen trennen.

## Release-Gates Build 159

1. CI-/Security-/Integrationsprüfungen erfolgreich;
2. exakt Build 159 testen;
3. First Boot erfolgreich;
4. Heimnetzübernahme + Reboot erfolgreich;
5. lokale GUI + Auth + Persistenz erfolgreich;
6. Cloud-Verbindung erfolgreich;
7. anschließend Plesk-Server aktualisieren;
8. Plesk-Plugin installieren und Cloud-V7-Verwaltung prüfen;
9. Entitlement/Freischaltung eines Test-Pi prüfen;
10. erst danach `CANDIDATE` → `VALIDATED`.

## Distribution

- Pi: `pi-universal-alpha-0.7.5-159`
- Android: GrowCentral Nexus Android APK
- iOS: GrowCentral Nexus iOS Sideload IPA
- APT Repository: `https://repo.dezender.de/apt`
- Public Project Console: `https://dezender.de`

## Projekttrennung

Das Repository `135er-Grow-Central` enthält ausschließlich Grow-Central-Inhalte. Fremdprojekte und fremde Deployments gehören nicht in dieses Repository.

## Design

Alle Oberflächen und Präsentationsassets folgen dem **GrowCentral Nexus UI**. Logo und Branding bleiben unverändert. Details: [`docs/DESIGN_SYSTEM_NEXUS.md`](docs/DESIGN_SYSTEM_NEXUS.md).
