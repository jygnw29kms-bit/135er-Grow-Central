<p align="center"><img src="docs/assets/brand/repository-banner-v0.9.png" alt="135er-Grow Central · Local-first Raspberry Pi control" width="100%"></p>

<p align="center">
  <a href="#deutsch"><strong>Deutsch</strong></a> · <a href="#english"><strong>English</strong></a> · <a href="docs/README.md">Docs</a> · <a href="docs/de/INSTALLATION.md">Installation</a> · <a href="SECURITY.md">Security</a>
</p>

<p align="center">
  <img alt="Version" src="https://img.shields.io/badge/version-alpha--0.7.1-71ff3b?style=flat-square&labelColor=061015">
  <img alt="Platform" src="https://img.shields.io/badge/platform-Raspberry%20Pi-35e8da?style=flat-square&labelColor=061015">
  <img alt="Status" src="https://img.shields.io/badge/status-hardware%20validation-ffb52b?style=flat-square&labelColor=061015">
  <img alt="Security" src="https://img.shields.io/badge/writes-deny%20by%20default-71ff3b?style=flat-square&labelColor=061015">
</p>

<p align="center"><code>LOCAL-FIRST</code> · <code>RASPBERRY PI</code> · <code>CLIMATE</code> · <code>POWER</code> · <code>SMART HOME</code></p>

> [!WARNING]
> **Alpha / hardware validation.** Device and protocol paths are still being verified. The Raspberry Pi remains the local authority; the optional cloud never replaces local control.

<table>
  <tr>
    <td width="25%"><strong>LOCAL CORE</strong><br><sub>FastAPI · SQLite · device policy</sub></td>
    <td width="25%"><strong>LOCAL GUI</strong><br><sub>Desktop · tablet · mobile</sub></td>
    <td width="25%"><strong>CLOUD VIEW</strong><br><sub>Optional · read-first</sub></td>
    <td width="25%"><strong>SECURITY</strong><br><sub>Approval · token · audit</sub></td>
  </tr>
</table>

## Deutsch

**135er-Grow Central** ist eine lokale Steuer- und Überwachungsplattform für Klima, Geräte, Energie und Automationen. Ein Raspberry Pi bildet die autoritative Master-Instanz. DF100M-BLE-Forschung, Smart Plugs, Home Assistant und eine optionale Cloud-Übersicht werden hinter klaren Vertrauensgrenzen zusammengeführt.

### Systemarchitektur

```text
Sensoren · DF100M · Smart Plugs
              │
              ▼
    135er-Grow Central Local
       Raspberry Pi Master
        │       │       │
     SQLite   FastAPI   Audit
        │
        └── ausgehendes HTTPS ──► optionale Cloud
```

| Ebene | Aufgabe | Vertrauensgrenze |
|---|---|---|
| **Local Core** | Geräte, Regeln, SQLite, API und Audit | Autoritativ |
| **Local GUI** | Bedienung auf Desktop, Tablet und Smartphone | Lokales Netz |
| **Cloud GUI** | Standortübergreifende Übersicht | Optional, read-first |
| **Public Website** | Projektpräsentation | Keine Steuerendpunkte |

### Sicherheitsmodell

Jeder Schreibzugriff durchläuft vier Gates: Das Gerät muss **bekannt**, **freigegeben**, separat als **beschreibbar** markiert und der Aufruf **authentifiziert** sein. `DF100M_ALLOW_WRITES`, Remote-Kommandos und Cloud-Steuerung bleiben standardmäßig deaktiviert.

### Schnellstart

```bash
git clone https://github.com/jygnw29kms-bit/135er-Grow-Central.git
cd 135er-Grow-Central
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --host 0.0.0.0 --port 8080
```

Weiterlesen: [Deutsche Dokumentation](docs/de/README.md) · [Installation](docs/de/INSTALLATION.md) · [Architektur](docs/de/ARCHITEKTUR.md) · [GUI-Zielbild](docs/de/GUI_VORSCHAU.md)

Das Raspberry-Pi-Testimage öffnet beim ersten Start den geschützten Zugangspunkt `135er-GrowCentral-Setup-XXXX`. Unter `https://10.42.0.1` werden WLAN/LAN, Hostname, Zeitzone und ein neues Gerätepasswort eingerichtet; erst danach startet der lokale Hauptdienst. [Anleitung zur Web-Ersteinrichtung](docs/de/RASPBERRY_PI_3B_TEST_IMAGE.md)

---

## English

**135er-Grow Central** is a local-first platform for climate, device, energy, and automation monitoring and control. A Raspberry Pi is the authoritative master instance. DF100M BLE research, smart plugs, Home Assistant, and an optional cloud overview are combined behind explicit trust boundaries.

### System architecture

```text
Sensors · DF100M · Smart Plugs
              │
              ▼
    135er-Grow Central Local
       Raspberry Pi Master
        │       │       │
     SQLite   FastAPI   Audit
        │
        └── outbound HTTPS ──► optional cloud
```

| Plane | Responsibility | Trust boundary |
|---|---|---|
| **Local Core** | Devices, rules, SQLite, API, and audit | Authoritative |
| **Local GUI** | Desktop, tablet, and mobile operation | Local network |
| **Cloud GUI** | Cross-site overview | Optional, read-first |
| **Public Website** | Project presentation | No control endpoints |

### Security model

Every write passes four gates: the device must be **known**, **approved**, explicitly marked **writable**, and the request must be **authenticated**. `DF100M_ALLOW_WRITES`, remote commands, and cloud control remain disabled by default.

### Quick start

```bash
git clone https://github.com/jygnw29kms-bit/135er-Grow-Central.git
cd 135er-Grow-Central
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --host 0.0.0.0 --port 8080
```

Continue with: [English documentation](docs/en/README.md) · [Installation](docs/en/INSTALLATION.md) · [Architecture](docs/en/ARCHITECTURE.md) · [GUI target](docs/en/GUI_PREVIEW.md)

On first boot, the Raspberry Pi test image exposes the protected `135er-GrowCentral-Setup-XXXX` access point. WLAN/LAN, hostname, timezone, and a new device password are configured at `https://10.42.0.1`; only then does the local main service start. [First-boot web provisioning guide](docs/en/RASPBERRY_PI_3B_TEST_IMAGE.md)

## Interface family / Interface-Familie

<table>
  <tr>
    <td width="50%"><img src="website/assets/gui/local-desktop-v0.9.png" alt="135er-Grow Central local desktop interface"><br><strong>Local Desktop</strong><br><sub>Full command center · Vollständige Kommandozentrale</sub></td>
    <td width="50%"><img src="website/assets/gui/local-tablet-v0.9.png" alt="135er-Grow Central local tablet interface"><br><strong>Local Tablet</strong><br><sub>Touch-first control surface</sub></td>
  </tr>
  <tr>
    <td width="50%"><img src="website/assets/gui/local-mobile-v0.9.png" alt="135er-Grow Central local mobile interface"><br><strong>Local Mobile</strong><br><sub>Compact local control · Kompakte lokale Kontrolle</sub></td>
    <td width="50%"><img src="website/assets/gui/cloud-desktop-v0.9.png" alt="135er-Grow Central optional cloud interface"><br><strong>Cloud Desktop</strong><br><sub>Optional remote overview · Optionale Remote-Übersicht</sub></td>
  </tr>
</table>

> [!NOTE]
> GUI values shown in the reference images are concept telemetry, not confirmed live measurements. / Die Werte in den Referenzbildern sind Konzept-Telemetrie und keine bestätigten Live-Messwerte.

## Repository map / Projektstruktur

| Path | Deutsch | English |
|---|---|---|
| `app/`, `shared/` | Lokale API und gemeinsame Modelle | Local API and shared models |
| `web/` | Lokale Control-GUI | Local control GUI |
| `cloud/` | Optionale Cloud-API und Übersicht | Optional cloud API and overview |
| `website/` | Öffentliche statische Website | Public static website |
| `image-builder/` | Raspberry-Pi-Image und Branding | Raspberry Pi image and branding |
| `docs/de/`, `docs/en/` | Zweisprachige technische Dokumentation | Bilingual technical documentation |
| `tests/` | Automatisierte Tests | Automated tests |

## Brand system / Markensystem

Repository, Website, lokale GUI, Cloud-GUI und Raspberry-Pi-Image verwenden dieselbe ruhige Control-Room-Ästhetik aus Near Black, Neon Lime, Data Cyan und Diagnostic Amber. Das Logo bleibt prominent; das kompakte `J.L.`-Markenzeichen sitzt zurückhaltend am Rand. Laufzeit-Assets werden als PNG ausgeliefert; WebP wird nicht verwendet.

Repository, website, local GUI, cloud GUI, and Raspberry Pi image share the same restrained control-room aesthetic built from near black, neon lime, data cyan, and diagnostic amber. The logo remains prominent while the compact `J.L.` mark stays subtle at the edge. Runtime assets are shipped as PNG; WebP is not used.

<p align="center"><img src="website/assets/brand/135er-grow-central-lockup-v0.9.png" alt="135er-Grow Central · J.L." width="760"></p>

<p align="center"><sub>Built local-first · Entwickelt local-first</sub></p>
