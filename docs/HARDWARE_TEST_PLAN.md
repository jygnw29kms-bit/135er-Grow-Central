# Hardware Test Plan – Build 159 / alpha-0.7.5

## Ziel

Reproduzierbare reale Validierung des aktuellen Raspberry-Pi-Images **Build 159**. CI-Erfolg und echter Hardwaretest werden strikt getrennt dokumentiert.

## Aktueller Testkandidat

- Release: `pi-universal-alpha-0.7.5-159`
- Image: `135er_Grow_Central_RPi3Plus_Universal_alpha-0.7.5-build-159.img.xz`
- SHA-256: `136ebc324595ccf732b4e48292b3cbf6a09e362846c53f2070190c44a3953f3b`
- Status vor Test: **CANDIDATE**

## Verbindliche Zugangsdaten- und Hostname-Semantik

- Hostname nach abgeschlossener Einrichtung: **`135er-GrowCentral.local`**
- **GUI-Zugangsdaten und System/SSH-Zugangsdaten sind getrennte Credentials.**
- Ein funktionierender GUI-Login beweist deshalb nicht automatisch einen funktionierenden SSH-/System-Login und umgekehrt.
- Beide Zugangspfade werden im Test getrennt geprüft und dokumentiert.

## Phase 1 – First Boot

1. Build 159 frisch flashen.
2. Keine manuellen Änderungen auf der Karte vornehmen.
3. Raspberry Pi starten.
4. Setup-AP `135er-GrowCentral-Setup-XXXX` verbinden.
5. `http://10.42.0.1/` öffnen.
6. First-Boot-Assistent vollständig durchlaufen.
7. Heim-WLAN auswählen oder SSID manuell eingeben.
8. System-/SSH-Zugangsdaten und GUI-Zugangsdaten getrennt wie vorgesehen setzen.
9. Setup abschließen.

### Muss funktionieren

- Setup-AP sichtbar;
- DHCP funktioniert;
- Portal erreichbar;
- WLAN-Konfiguration speicherbar;
- GUI- und System/SSH-Zugangsdaten werden getrennt behandelt;
- kein ungeschützter Normalbetrieb während First Boot;
- verständliche Fehleranzeige bei Problemen.

## Phase 2 – Reboot ins Heimnetz

1. Pi sauber rebooten.
2. Prüfen, ob Setup-AP verschwindet bzw. First Boot als abgeschlossen gilt.
3. Prüfen, ob der Pi im Heimnetz eine Adresse erhält.
4. `http://135er-GrowCentral.local/` testen.
5. Falls mDNS nicht greift, IP-Adresse im Router ermitteln und direkt testen.
6. GUI-Login mit den **GUI-Zugangsdaten** durchführen.
7. System/SSH-Zugang separat mit den **System/SSH-Zugangsdaten** prüfen.
8. Prüfen, ob First-Boot-Einstellungen nach Reboot erhalten bleiben.
9. Netzwerkstatus in der GUI kontrollieren.

### Muss funktionieren

- Boot ohne manuelle Reparatur;
- Heimnetzverbindung automatisch;
- Hostname `135er-GrowCentral.local` erreichbar, sofern mDNS im Netz funktioniert;
- GUI erreichbar;
- GUI-Login erforderlich;
- GUI- und System/SSH-Credentials voneinander getrennt;
- Einstellungen persistent.

## Phase 3 – Cloud-Anbindung

Nach erfolgreichem lokalen Reboot:

1. Cloud-Verbindungsstatus prüfen.
2. Prüfen, ob sich der Pi eindeutig mit seiner Geräteidentität meldet.
3. Verhalten ohne vorhandene Freischaltung dokumentieren.
4. Prüfen, ob Cloud V7 den Pi sehen bzw. dessen Status verarbeiten kann.
5. Nach Installation des Serverplugins später Entitlements für genau dieses Testgerät setzen.
6. Pi-Abruf der effektiven Entitlements prüfen.
7. Sicherstellen, dass lokale Grundfunktionen bei nicht verfügbarer Cloud weiter funktionieren.

## Phase 4 – Plesk-Server vorbereiten

**Noch vor Installation des Grow-Central-Plesk-Plugins:**

```bash
sudo apt update
sudo apt upgrade
sudo apt --fix-broken install
sudo systemctl --failed
```

Danach prüfen:

- Plesk Panel erreichbar;
- Webserver/Reverse Proxy läuft;
- PHP/Python-Abhängigkeiten unauffällig;
- Datenbank läuft;
- keine fehlgeschlagenen systemd-Dienste, die für Plesk relevant sind.

Wenn Kernel, libc, systemd oder andere zentrale Komponenten aktualisiert wurden: kontrollierter Reboot und danach Plesk erneut prüfen.

## Phase 5 – Plesk-Plugin / Cloud V7

Erst wenn Phase 4 sauber ist:

1. Grow-Central-Plesk-Plugin installieren.
2. Plugin-Menü und Setup öffnen.
3. Cloud-V7-Dienste prüfen.
4. Test-Pi in der Geräteverwaltung prüfen.
5. Kunde/Gruppe/Status/Plan setzen.
6. einzelne Features manuell freischalten.
7. Pi die effektiven Entitlements abrufen lassen.
8. Änderung zurücknehmen und erneuten Abruf prüfen.
9. Fehlerfall testen: unbekanntes Gerät / gesperrtes Gerät / abgelaufene Freischaltung.

## Cloud-V7-Entitlements

Der aktuelle Stand sieht folgende schaltbare Features vor:

- `remote_control`
- `camera`
- `history_extended`
- `alerts`
- `automation_pro`
- `api_access`
- `beta_features`

## Erweiterter Hardwaretest nach Baseline

Wenn First Boot, Heimnetz und Cloud funktionieren, folgen die Gerätepfade:

- FRITZ! Smart Home;
- TP-Link Tapo;
- Logitech C920/UVC;
- Bluetooth-Scan;
- Mars Hydro / iConnect Diagnose;
- Elecrow Touch/Kiosk;
- Räume/Grow/Automationen;
- Supportdatei und Schwärzung sensibler Daten.

## Testprotokoll

| ID | Bereich | Erwartung | Ergebnis |
|---|---|---|---|
| B159-01 | Flash/Boot | Image startet | TBD |
| B159-02 | Setup-AP | AP + DHCP vorhanden | TBD |
| B159-03 | First Boot | Setup vollständig möglich | in Prüfung |
| B159-04 | WLAN | Heimnetz gespeichert | TBD |
| B159-05 | Reboot | Pi startet im Heimnetz | TBD |
| B159-06 | Hostname | `135er-GrowCentral.local` erreichbar | TBD |
| B159-07 | GUI Auth | GUI-Credentials funktionieren | TBD |
| B159-08 | System/SSH Auth | separate System/SSH-Credentials funktionieren | TBD |
| B159-09 | Cloud | Verbindung nachvollziehbar | TBD |
| SRV-01 | APT Update | Server aktualisiert fehlerfrei | TBD |
| SRV-02 | Reboot/Plesk | Plesk danach gesund | TBD |
| V7-01 | Plugin | Installation/Setup erfolgreich | TBD |
| V7-02 | Geräteverwaltung | Test-Pi sichtbar | TBD |
| V7-03 | Entitlement | Freischaltung kommt am Pi an | TBD |

## VALIDATED-Gate

Build 159 wird erst auf **VALIDATED** gesetzt, wenn mindestens folgende Punkte real bestätigt sind:

- First Boot;
- WLAN-Übernahme;
- Reboot ins Heimnetz;
- Hostname `135er-GrowCentral.local` bzw. direkter IP-Zugriff;
- lokale GUI/Auth/Persistenz;
- separater System/SSH-Zugang;
- Cloud-Anbindung;
- nachvollziehbarer Cloud-V7-Gerätepfad.

Weitere Geräteintegrationen können anschließend einzeln validiert werden; ein erfolgreicher Build allein ist keine Hardwarevalidierung.
