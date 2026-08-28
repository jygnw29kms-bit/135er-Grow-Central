<p align="center"><img src="docs/assets/brand/repository-banner-v0.9.png" alt="135er-Grow Central · GrowCentral Nexus UI" width="100%"></p>

<p align="center">
  <a href="#deutsch"><strong>Deutsch</strong></a> · <a href="#english"><strong>English</strong></a> · <a href="RELEASE_STATE.md"><strong>Release State</strong></a> · <a href="docs/HARDWARE_TEST_PLAN.md"><strong>Hardware Test</strong></a> · <a href="SECURITY.md">Security</a>
</p>

<p align="center">
  <img alt="Version" src="https://img.shields.io/badge/version-alpha--0.7.5-71ff3b?style=flat-square&labelColor=061015">
  <img alt="Pi Candidate" src="https://img.shields.io/badge/Pi%20candidate-Build%20159-ffb52b?style=flat-square&labelColor=061015">
  <img alt="Cloud" src="https://img.shields.io/badge/Cloud-V7-35e8da?style=flat-square&labelColor=061015">
  <img alt="Design" src="https://img.shields.io/badge/UI-GrowCentral%20Nexus-2ae5ff?style=flat-square&labelColor=061015">
</p>

# Deutsch

**135er-Grow Central** ist eine local-first Steuer-, Überwachungs- und Automationsplattform für Raspberry Pi mit optionaler eigener Cloud-Anbindung.

## Aktueller Stand · 28.08.2026

| Bereich | Stand |
|---|---|
| Repository | `master` |
| Version | `alpha-0.7.5` |
| Pi-Testkandidat | **Build 159** |
| Release | `pi-universal-alpha-0.7.5-159` |
| Status | **CANDIDATE** |
| Cloud | **V7** |
| Server | Plesk + Standalone vorgesehen |
| APT | Update-/Upgradepfad vorgesehen |
| Design | GrowCentral Nexus UI |

### Aktuelles Pi-Image

`135er_Grow_Central_RPi3Plus_Universal_alpha-0.7.5-build-159.img.xz`

SHA-256:

`136ebc324595ccf732b4e48292b3cbf6a09e362846c53f2070190c44a3953f3b`

Build 159 bleibt **CANDIDATE**, bis der reale Hardwaretest bestanden ist.

## Nächster realer Test

Der aktuelle Testpfad ist bewusst kurz und eindeutig:

1. Build 159 frisch flashen.
2. First Boot über Setup-AP durchführen.
3. Heim-WLAN konfigurieren.
4. Setup abschließen.
5. Raspberry Pi rebooten.
6. Erreichbarkeit im Heimnetz prüfen.
7. GUI/Login/Persistenz prüfen.
8. Cloud-Anbindung prüfen.
9. Danach erst den Plesk-Server aktualisieren.
10. Danach Grow-Central-Plesk-Plugin installieren und Cloud V7 testen.

Ausführlich: [`docs/HARDWARE_TEST_PLAN.md`](docs/HARDWARE_TEST_PLAN.md).

## Cloud V7

Cloud V7 enthält die Grundlage für die spätere zentrale Geräte- und Freischaltungsverwaltung:

- Plesk- und Standalone-Routing;
- Admin- und Entitlement-Endpunkte;
- Geräte-/Kunden-Zuordnung;
- Gerätegruppen;
- Status, Plan und Laufzeit;
- manuell schaltbare Feature-Entitlements;
- sicherer Abruf der effektiven Freischaltungen durch die Pis;
- APT-Paketierung und Upgradepfad;
- CI-Validierung der V7-Routen;
- gehärtete Entitlement-Updates.

Aktuell vorgesehene Feature-Schalter:

- `remote_control`
- `camera`
- `history_extended`
- `alerts`
- `automation_pro`
- `api_access`
- `beta_features`

## Plesk-Vorbereitung

Vor Installation des Grow-Central-Plesk-Plugins zuerst das Serverbetriebssystem sauber aktualisieren:

```bash
sudo apt update
sudo apt upgrade
sudo apt --fix-broken install
sudo systemctl --failed
```

Wenn zentrale Systemkomponenten aktualisiert wurden, Server kontrolliert rebooten und **Plesk erst vollständig prüfen**, bevor das Grow-Central-Plugin installiert wird.

Damit bleiben zwei Fehlerklassen sauber getrennt:

- Betriebssystem/Plesk-Update
- Grow-Central-Plugin/Cloud V7

## Local-First

Der Raspberry Pi bleibt die autoritative lokale Instanz. Cloud-Funktionen ergänzen den lokalen Betrieb und sollen ihn nicht unnötig blockieren.

Typische lokale Bereiche:

- First Boot und Netzwerk;
- GUI/Auth;
- Räume und Grow;
- Automationen;
- FRITZ! Smart Home;
- Tapo;
- Logitech C920/UVC;
- Mars-Hydro-/Bluetooth-Diagnose;
- Systemdiagnose und Supportdateien.

## Zugriff

- First Boot: `http://10.42.0.1/`
- lokal nach Einrichtung: `http://135er-Grow-Central.local/`
- Port `8080`: Kompatibilitätspfad

## Mobile

Mobile Apps bleiben Clients der Grow-Central-Plattform und ersetzen den Pi nicht.

- Android: APK
- iOS: Sideload IPA

## Projekttrennung

Dieses Repository enthält **ausschließlich 135er-Grow-Central**. Fremde Websites, Deployments und andere Projekte gehören nicht in dieses Repository.

## Kanonische Dokumente

- [`RELEASE_STATE.md`](RELEASE_STATE.md)
- [`docs/HARDWARE_TEST_PLAN.md`](docs/HARDWARE_TEST_PLAN.md)
- [`docs/DESIGN_SYSTEM_NEXUS.md`](docs/DESIGN_SYSTEM_NEXUS.md)
- [`SECURITY.md`](SECURITY.md)

---

# English

**135er-Grow Central alpha-0.7.5** is a local-first Raspberry Pi control, monitoring and automation platform with an optional self-hosted cloud layer.

The current Raspberry Pi hardware-test candidate is **Build 159** (`pi-universal-alpha-0.7.5-159`). It remains **CANDIDATE** until a real First Boot → home-network reboot → local GUI → cloud-connectivity test succeeds.

Cloud **V7** adds Plesk and standalone routing, device/customer/group management, manual feature entitlements, secure Pi entitlement retrieval, APT packaging and upgrade support.

The next validation sequence is: flash Build 159, complete First Boot, join the home network, reboot, verify local operation, verify cloud connectivity, then update the Plesk host and install the Grow-Central Plesk plugin.

Canonical status: [`RELEASE_STATE.md`](RELEASE_STATE.md).
