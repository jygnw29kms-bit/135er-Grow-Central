<p align="center"><img src="docs/assets/brand/repository-banner-v0.9.png" alt="135er-Grow Central · Local-first Raspberry Pi control" width="100%"></p>

<p align="center">
  <a href="#deutsch"><strong>Deutsch</strong></a> · <a href="#english"><strong>English</strong></a> · <a href="docs/README.md">Docs</a> · <a href="docs/de/INSTALLATION.md">Installation</a> · <a href="docs/RELEASE_PIPELINE.md">Release Status</a> · <a href="SECURITY.md">Security</a>
</p>

<p align="center">
  <img alt="Version" src="https://img.shields.io/badge/version-alpha--0.7.5-71ff3b?style=flat-square&labelColor=061015">
  <img alt="Platform" src="https://img.shields.io/badge/platform-Raspberry%20Pi%203B-35e8da?style=flat-square&labelColor=061015">
  <img alt="Baseline" src="https://img.shields.io/badge/validated%20baseline-Build%2085-71ff3b?style=flat-square&labelColor=061015">
  <img alt="Status" src="https://img.shields.io/badge/status-alpha%20hardware%20validation-ffb52b?style=flat-square&labelColor=061015">
</p>

<p align="center"><code>LOCAL-FIRST</code> · <code>RASPBERRY PI</code> · <code>FRITZ! SMART HOME</code> · <code>TAPO</code> · <code>LOGITECH C920</code> · <code>MARS HYDRO iCONNECT</code> · <code>SIGNED APT</code></p>

> [!WARNING]
> **Alpha / Hardwarevalidierung.** Build 85 ist die aktuell dokumentierte validierte Raspberry-Pi-Basis. Der `master` enthält bereits weitere Änderungen und erneut ausgelöste Image-Builds; diese gelten erst nach realem Zieltest als neue validierte Basis.

## Deutsch

**135er-Grow Central** ist eine local-first Steuer-, Überwachungs- und Automationsplattform. Der Raspberry Pi bleibt die autoritative lokale Instanz für GUI, Gerätepolicy, Smart Home, Kamera, Diagnose und optionale Cloud-/Server-Anbindung.

### Aktueller Projektstand – 23.08.2026

Repository-Version: **alpha-0.7.5**  
Dokumentierte validierte Image-Basis: **Build 85**  
Branch: **master**

Der aktuelle Entwicklungsstand umfasst unter anderem:

- dauerhafte Geräte-Registry über Browser- und Pi-Neustarts;
- verschlüsselte wiederverwendbare FRITZ!Box- und Tapo-Zugangsdaten mit restriktiven Dateirechten;
- FRITZ!SmartHome-Import, Livewerte, Schalten, Routinen und Templates;
- Stromkosten auf Basis der gemeldeten Gesamtenergie, sodass historische Kosten auch bei ausgeschalteter Steckdose sichtbar bleiben;
- No-Cache-Liveprüfung bei Menüwechseln und eine eindeutige Offline-Ansicht bei Pi-Ausfall;
- lokales authentifiziertes Tapo-Onboarding über alle aktiven IPv4-Netze des Pi mit dauerhafter Geräteübernahme;
- Logitech-C920/UVC-Erkennung, Snapshot, native MJPEG-Modi und dynamische V4L2-Regler;
- Mars-Hydro/iConnect-Zielarchitektur mit BLE-Diagnose-/Fallback-Pfad;
- First-Boot-Setup, GUI-Login/Sessions, Diagnose und geschwärzte Support-Pakete;
- Cloud-/Server-Installer V6;
- signiertes APT-Repository unter `https://repo.dezender.de/apt`;
- automatische Veröffentlichung der Website und Server-Hilfsskripte nach `dezender.de`.

Die frühere öffentliche Build-70→71→72-Roadmap ist nicht mehr der aktuelle Projektstand. Maßgeblich ist die aktuelle Release-Dokumentation unter [`docs/RELEASE_PIPELINE.md`](docs/RELEASE_PIPELINE.md).

### First Boot

Der First-Boot-Ablauf liegt in der geschützten Haupt-GUI unter **System**:

1. **Systempasswort ändern – Pflicht**
2. **Heimnetz einrichten** – aktives LAN erkennen oder WLAN auswählen/manuell eintragen
3. **FRITZ!Box optional anbinden** – eigener Benutzer mit notwendigen Smart-Home-Rechten empfohlen
4. **Grow-Central-GUI absichern – Pflicht** – eigener GUI-Benutzer und mindestens 12 Zeichen langes Passwort

Setup-WLAN: `135er-GrowCentral-Setup-XXXX`  
First-Boot-Adresse: `http://10.42.0.1/`  
Nach Einrichtung: `http://135er-Grow-Central.local/`  
Port `8080` bleibt als Kompatibilitätsadresse erhalten.

### Support und Diagnose

Unter **System → Support-Datei erstellen** kann jederzeit `Grow-Central-Support-latest.tar.gz` erzeugt werden. Passwörter, Tokens, Cookies, PSKs und Hashwerte werden entfernt; technische Netzwerk- und Hardwarekennungen bleiben für die Fehleranalyse erhalten. Bei einem realen Problem ist dieses Paket die bevorzugte Diagnosebasis.

### FRITZ! Smart Home

Der lokale AVM/AHA-Pfad unterstützt bei kompatiblen Geräten unter anderem:

- erreichbar / offline;
- Schaltzustand und Ein/Aus;
- Gerätename, AIN, Modell, Firmware und Funktionsklassen;
- aktuelle Leistung;
- Gesamtenergie;
- Spannung;
- Umgebungstemperatur und Temperatur-Offset, sofern vom Gerät gemeldet;
- Routinen und Templates auf den dafür vorgesehenen Pfaden.

Die erste erfolgreich geprüfte Anmeldung kann verschlüsselt lokal gespeichert und anschließend automatisch für freigegebene Aktionen wiederverwendet werden. Das Passwort wird nicht an Browser-APIs zurückgegeben.

### TP-Link Tapo

Tapo ist als **hybride Integration** ausgelegt. Der aktuelle Adapter implementiert den authentifizierten lokalen `python-kasa`-Pfad, durchsucht aktive IPv4-Netze und übernimmt bestätigte Geräte dauerhaft mit den lokal verfügbaren Metadaten.

Die private TP-Link-Cloud-Inventarisierung wird nicht als implementiert dargestellt, solange dafür kein eigener validierter WAN-/Cloud-Pfad vorliegt.

### Energie, Kosten und History

Stromkosten werden aus der gemeldeten Gesamtenergie und dem konfigurierten Tarif abgeleitet. Dadurch bleibt bereits entstandener Verbrauch bzw. Kostenstand sichtbar, wenn eine Steckdose ausgeschaltet ist; nur Live-Leistungsprognosen gehen bei 0 W auf null.

Die weitere Auswertung ist auf frei wählbare Zeiträume wie Stunde, Tag, Monat und Jahr sowie History-/Chart-Darstellung ausgerichtet.

### Logitech C920 / UVC

Die Referenzkamera ist die Logitech C920. Unterstützt werden – soweit vom jeweiligen V4L2-Gerät tatsächlich gemeldet – Erkennung, Capture-Fähigkeit, JPEG-Snapshot, native MJPEG-Auflösungen, Livebild sowie dynamische Kamera-Regler wie Helligkeit, Kontrast, Sättigung, Weißabgleich, Belichtung, Fokus und Zoom.

Browser-Eingaben dürfen keine beliebigen Device-Pfade oder unbekannte V4L2-Controlnamen direkt an den Server durchreichen.

### Mars Hydro

| Gerät | Projektdefinition | Integrationsrichtung |
|---|---|---|
| **Mars Hydro FC3000** | Modelljahr 2024, USB, iConnect | gemeinsame iConnect-Gerätefamilie |
| **Mars Hydro DF100 / iFresh** | iFresh-Serie mit iConnect | gemeinsame iConnect-Gerätefamilie |
| **DF100M / MZ_MZF002** | beobachteter BLE-Pfad | Diagnose / Reverse Engineering / Fallback |

Unbekannte oder nicht reproduzierbar validierte Mars-Hydro-Schreibtelegramme bleiben gesperrt.

### Cloud / Server / APT

Für den Serverpfad stehen aktuell bereit:

- `scripts/install-135ercloud-v6.sh`
- `scripts/setup-135ercloud-apt-repo-v1.sh`
- APT: `https://repo.dezender.de/apt`

Die APT-Einrichtung verwendet einen dedizierten `Signed-By`-Keyring und bereinigt alte Grow-Central-Quellen, bevor die kanonische Quelle eingetragen wird. Die Website-Deployment-Pipeline veröffentlicht die aktuellen Installer zusätzlich im Webroot von `dezender.de`.

### Sicherheitsmodell

- Smart-Home-Code bleibt standardmäßig **deny-by-default**.
- Schreiboperationen benötigen eine authentifizierte GUI-Sitzung oder ein explizites API-Token.
- Geräte müssen bekannt, freigegeben und beschreibbar sein.
- GUI-Passwörter werden als PBKDF2-SHA256-Verifier gespeichert.
- Integrationspasswörter werden nicht absichtlich geloggt oder an Browser-APIs zurückgegeben.
- Remote-Zugriff benötigt zusätzlich TLS/HTTPS bzw. einen entsprechend abgesicherten Reverse-Proxy/VPN-Pfad.
- Die öffentliche Website besitzt keine direkten lokalen Steuerendpunkte.

### Architektur

```text
Clients im LAN / optional abgesicherter Remote-Zugang
                         │
                  GUI Login / Session
                         │
                         ▼
              135er-Grow Central Local
                    Raspberry Pi
        ┌────────────────┼─────────────────┐
        │                │                 │
   Mars Hydro       Smart Home          Kamera
 FC3000/iFresh   FRITZ! / Tapo        C920 / UVC
        │                │                 │
 iConnect/BLE       local APIs          V4L2
 diagnostics         + policy           ffmpeg
                         │
                  optional Server
                  HTTPS / Cloud V6
```

Weiterlesen: [Installation](docs/de/INSTALLATION.md) · [Integrationen](docs/de/INTEGRATIONEN.md) · [Release-Status](docs/RELEASE_PIPELINE.md) · [Hardware-Testplan](docs/HARDWARE_TEST_PLAN.md) · [Mars Hydro / iConnect](docs/MARS_HYDRO_ICONNECT.md)

---

## English

**135er-Grow Central alpha-0.7.5** is a local-first Raspberry Pi control, monitoring and automation platform. **Build 85 is the currently documented validated hardware baseline**; `master` already contains newer integration, test, APT, cloud and image-pipeline changes that require hardware validation before they become the next validated baseline.

Current capabilities include persistent device registration, encrypted reusable FRITZ!/Tapo credentials, local FRITZ! Smart Home telemetry and control, authenticated local Tapo discovery, retained energy-cost accounting, live/offline GUI checks, C920/UVC support, Mars Hydro iConnect/BLE diagnostics, first-boot security, redacted support bundles, a V6 server installer and a signed APT repository at `https://repo.dezender.de/apt`.

Mobile remains a WebGUI client rather than a Raspberry-Pi replacement. Remote operation must use a secured HTTPS server path; local device authority and write policy remain on Grow Central.

Continue with: [English documentation](docs/en/README.md) · [Integrations](docs/en/INTEGRATIONS.md) · [Release status](docs/RELEASE_PIPELINE.md) · [Hardware test plan](docs/HARDWARE_TEST_PLAN.md)

## Interface family / Interface-Familie

<table>
  <tr>
    <td width="50%"><img src="website/assets/gui/local-desktop-v0.9.png" alt="135er-Grow Central local desktop interface"><br><strong>Local Desktop</strong></td>
    <td width="50%"><img src="website/assets/gui/local-tablet-v0.9.png" alt="135er-Grow Central local tablet interface"><br><strong>Local Tablet</strong></td>
  </tr>
  <tr>
    <td width="50%"><img src="website/assets/gui/local-mobile-v0.9.png" alt="135er-Grow Central local mobile interface"><br><strong>Local Mobile</strong></td>
    <td width="50%"><img src="website/assets/gui/cloud-desktop-v0.9.png" alt="135er-Grow Central optional cloud interface"><br><strong>Cloud Desktop</strong></td>
  </tr>
</table>

> [!NOTE]
> GUI preview values are concept telemetry unless explicitly marked as hardware-validated.

<p align="center"><img src="website/assets/brand/135er-grow-central-lockup-v0.9.png" alt="135er-Grow Central · J.L." width="760"></p>
