<p align="center"><img src="docs/assets/brand/repository-banner-v0.9.png" alt="135er-Grow Central Â· Local-first Raspberry Pi control" width="100%"></p>

<p align="center">
  <img alt="Version" src="https://img.shields.io/badge/version-alpha--0.7.1-71ff3b?style=flat-square&labelColor=061015">
  <img alt="Platform" src="https://img.shields.io/badge/platform-Raspberry%20Pi-35e8da?style=flat-square&labelColor=061015">
  <img alt="Status" src="https://img.shields.io/badge/status-WIP-ffb52b?style=flat-square&labelColor=061015">
  <img alt="Writes" src="https://img.shields.io/badge/writes-deny%20by%20default-71ff3b?style=flat-square&labelColor=061015">
</p>

<p align="center"><strong>LOCAL-FIRST Â· RASPBERRY PI Â· CLIMATE Â· POWER Â· SMART HOME</strong></p>

> [!WARNING]
> **Work in Progress:** Hardware- und Protokollpfade werden weiter validiert. Der Raspberry Pi bleibt die lokale AutoritÃ¤t; die optionale Cloud ersetzt niemals die lokale Steuerung.

## System

135er-Grow Central ist eine lokale Steuer- und Ãœberwachungsplattform fÃ¼r Klima, GerÃ¤te, Energie und Automationen. Die Plattform verbindet einen Raspberry Pi mit DF100M-BLE-Experimenten, Smart Plugs, optionalem Home Assistant und einer strikt getrennten Cloud-Ãœbersicht.

| Control Plane | Funktion | Vertrauensgrenze |
|---|---|---|
| **Local Core** | FastAPI, SQLite, GerÃ¤te, Regeln und Audit | Autoritativ |
| **Local GUI** | Desktop-, Tablet- und Mobile-Steuerung | Lokales Netz |
| **Cloud GUI** | Optionale standortÃ¼bergreifende Ãœbersicht | Read-first |
| **Public Website** | Statische ProjektprÃ¤sentation | Keine Steuerendpunkte |

```text
Sensors Â· DF100M Â· Smart Plugs
              â”‚
              â–¼
    135er-Grow Central Local
       Raspberry Pi Master
        â”‚       â”‚       â”‚
     SQLite   FastAPI   Audit
        â”‚
        â””â”€â”€ outbound HTTPS â”€â”€â–º optional cloud
```

## Interface-Familie v0.9

<table>
  <tr>
    <td width="50%"><img src="website/assets/gui/local-desktop-v0.9.png" alt="Local Desktop"><br><strong>Local Desktop</strong> Â· vollstÃ¤ndige Kommandozentrale</td>
    <td width="50%"><img src="website/assets/gui/local-tablet-v0.9.png" alt="Local Tablet"><br><strong>Local Tablet</strong> Â· Touch-first Control Surface</td>
  </tr>
  <tr>
    <td width="50%"><img src="website/assets/gui/local-mobile-v0.9.png" alt="Local Mobile"><br><strong>Local Mobile</strong> Â· kompakte lokale Kontrolle</td>
    <td width="50%"><img src="website/assets/gui/cloud-desktop-v0.9.png" alt="Cloud Desktop"><br><strong>Cloud Desktop</strong> Â· optionale Remote-Ãœbersicht</td>
  </tr>
</table>

Die dargestellten Werte sind Konzept-Telemetrie und keine bestÃ¤tigten Live-Messwerte.

## Sicherheitsmodell

Jeder Schreibzugriff durchlÃ¤uft vier Gates:

1. **Inventory** â€“ GerÃ¤t ist bekannt.
2. **Approval** â€“ GerÃ¤t wurde explizit freigegeben.
3. **Writable** â€“ Write-Recht wurde separat aktiviert.
4. **Authenticated** â€“ TokenprÃ¼fung und Audit sind erfolgreich.

StandardmÃ¤ÃŸig bleiben `DF100M_ALLOW_WRITES`, Remote-Kommandos und Cloud-Steuerung deaktiviert.

## Raspberry-Pi-Test-Image

Der reproduzierbare Image-Workflow installiert Anwendung und AbhÃ¤ngigkeiten, richtet Bluetooth, Firewall, SSH und systemd ein und integriert den aktuellen 135er-Grow-Central-Boot-Splash.

- Raspberry Pi OS Lite 64-bit / Debian 13
- Raspberry Pi 3B / 3B+
- fester Headless-Benutzer: `GrowCentral` (temporÃ¤res Passwort: `test`)
- Deutsch (`de_DE.UTF-8`), Zeitzone `Europe/Berlin`, Tastatur `de(nodeadkeys)`
- keine interaktive Benutzer- oder Tastaturabfrage beim ersten Start
- UFW: nur TCP 22 und 8080
- BLE- und Remote-Writes standardmÃ¤ÃŸig deaktiviert

FÃ¼r Tests ohne Raspberry Pi gibt es ein getrenntes Debian-ARM64-QEMU-Image. Es verwendet einen fÃ¼r virtuelle Hardware geeigneten Kernel und wird vor der VerÃ¶ffentlichung automatisch Ã¼ber `/api/health` geprÃ¼ft. WeboberflÃ¤che und SSH sind unter Windows Ã¼ber `localhost:8080` und Port `2222` erreichbar. Bluetooth, GPIO und DF100M-Funk bleiben Hardwaretests.

Details: [Raspberry-Pi-Image](docs/de/RASPBERRY_PI_3B_TEST_IMAGE.md) Â· [Image Builder](image-builder/README.md)

## Projektstruktur

| Pfad | Inhalt |
|---|---|
| `app/`, `shared/` | lokale API und gemeinsame Modelle |
| `web/` | lokale Control-GUI |
| `cloud/` | optionale Cloud-API und Ãœbersicht |
| `website/` | Ã¶ffentliche statische Website |
| `image-builder/` | Raspberry-Pi-Image-Branding und Build-Doku |
| `docs/` | Architektur, Sicherheit, Protokoll und Betrieb |
| `tests/` | automatisierte Tests |

## Einstieg

```bash
git clone https://github.com/jygnw29kms-bit/135er-Grow-Central.git
cd 135er-Grow-Central
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --host 0.0.0.0 --port 8080
```

Dokumentation: [Deutsch](docs/de/README.md) Â· [English](docs/en/README.md) Â· [Architektur](docs/ARCHITECTURE_MASTER.md) Â· [Security](docs/SECURITY_AND_TRUST_MODEL.md)

## Branding

Die verbindliche Marke kombiniert Symbol, Wortmarke und das grafische `J.L.`-Signet. Repository, Website, lokale GUI, Cloud-GUI und Raspberry-Pi-Image verwenden dieselbe Near-Black-, Neon-Lime- und Cyan-Designsprache. Laufzeit-Branding wird als PNG ausgeliefert; WebP wird nicht verwendet.

<p align="center"><img src="website/assets/brand/135er-grow-central-lockup-v0.9.png" alt="135er-Grow Central Â· J.L." width="760"></p>
