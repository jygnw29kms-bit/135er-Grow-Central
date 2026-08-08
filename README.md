# 135er GrowControl

**DE:** Local-First Raspberry-Pi-Steuerplattform mit optionaler Linux-VServer-Cloud.  
**EN:** Local-first Raspberry Pi control platform with an optional Linux VPS cloud layer.

Aktueller Gerätefokus / Current device focus: **Mars Hydro DF100M / MZ_MZF002**  
**Kein ESP32 erforderlich / No ESP32 required**

![Version](https://img.shields.io/badge/version-0.5.0-35f0a7)
![Platform](https://img.shields.io/badge/platform-Debian%20%7C%20Ubuntu%20%7C%20Raspberry%20Pi-c51a4a)
![Cloud](https://img.shields.io/badge/cloud-optional-32ccff)
![Docs](https://img.shields.io/badge/docs-DE%20%7C%20EN-8e6cff)
![License](https://img.shields.io/badge/license-MIT-blue)

## GUI Zielbild / GUI Target

Die folgende Vorschau ist die aktuelle **Design-Referenz für die fertige 135er-GrowControl-GUI**. Die reale Oberfläche wird responsiv umgesetzt und passt Struktur, Navigation, Karten und Diagramme an Desktop, Notebook, Tablet/iPad und Smartphone an.

The following preview is the current **design reference for the finished 135er GrowControl GUI**. The real interface will be responsive and will adapt layout, navigation, cards and charts to desktop, notebook, tablet/iPad and smartphone devices.

![135er GrowControl GUI Preview](docs/assets/gui/gui-preview-v0.5.webp)

- 🇩🇪 [GUI-Zielbild und Responsive Design](docs/de/GUI_VORSCHAU.md)
- 🇬🇧 [GUI Target and Responsive Design](docs/en/GUI_PREVIEW.md)

## Dokumentation / Documentation

- 🇩🇪 [Deutsch](docs/de/README.md)
- 🇬🇧 [English](docs/en/README.md)
- 📚 [Dokumentationsindex / Documentation index](docs/README.md)
- 📖 [Wiki-Quelle / Wiki source](wiki/Home.md)
- 🔎 [Quellen / Sources](docs/SOURCES.md)

> **Wiki:** Die vollständige Wiki-Quelle wird versioniert im Verzeichnis `wiki/` gepflegt. Das GitHub-Wiki-Repository ist derzeit noch nicht aktiviert/erreichbar; nach Aktivierung kann dieser Inhalt 1:1 in das GitHub-Wiki gespiegelt werden.  
> **Wiki:** The complete wiki source is versioned in `wiki/`. The GitHub wiki repository is currently not enabled/reachable; once enabled, this content can be mirrored 1:1 into the GitHub Wiki.

## Architektur / Architecture

```text
                  iPad / Browser
                       │
                       ▼
            135er GrowControl Local
                 Raspberry Pi
                 │         │
              BLE│         └──── HTTPS ───► GrowControl Cloud
                 ▼                         Linux VPS
              DF100M                       │
                                          ├─ Telemetry
                                          ├─ History
                                          └─ Remote Overview
```

**DE:** Der Raspberry Pi bleibt immer die lokale Steuerinstanz. Die Cloud ist optional.  
**EN:** The Raspberry Pi always remains the local control node. The cloud is optional.

## Plattform / Platform

Die Full-Platform-Baseline ist auf Debian-/Ubuntu-Systeme ausgerichtet:

- Debian 12 / 13
- Ubuntu Server 22.04 / 24.04 LTS
- Raspberry Pi OS 64-bit auf Debian-Basis
- systemd
- APT / unattended-upgrades
- Nginx / HTTPS
- Firewall / Fail2ban
- SQLite lokal / PostgreSQL Cloud
- Benutzer, Rollen und Rechte (RBAC)
- Sensoren, Historie, Zeitpläne und Automationen
- Audit-Log, Backup/Restore und Fail-Safe-Synchronisation

## Status

| Bereich / Area | Status |
|---|---|
| BLE Discovery | ✅ implemented |
| BLE Connect / Disconnect | ✅ implemented |
| GATT Inspection | ✅ implemented |
| Notification Capture | 🧪 experimental |
| DF100M Speed Protocol | 🧪 not validated |
| Future HUD / Responsive Target | ✅ defined |
| Cloud Telemetry | 🧪 alpha |
| Cloud History | 🧪 alpha |
| RBAC / Database baseline | ✅ defined |
| Installer / Debian-Ubuntu baseline | ✅ defined |
| Remote Commands | 🔒 prepared, disabled by default |
| FC3000 Adapter | 🗺️ planned |
| Sensor / VPD Automation | 🗺️ platform prepared |

## Quick Start / Schnellstart

### Raspberry Pi

```bash
sudo apt update
sudo apt install -y git python3 python3-pip python3-venv bluetooth bluez

git clone https://github.com/jygnw29kms-bit/135er_GrowControl.git
cd 135er_GrowControl

python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

cp .env.example .env
uvicorn app.main:app --host 0.0.0.0 --port 8080
```

Öffnen / Open:

```text
http://PI-IP:8080
```

### Optional Cloud / Optionale Cloud

```bash
cp cloud/.env.example cloud/.env
# DE: sicheren Token setzen
# EN: set a secure token

docker compose -f docker-compose.cloud.yml up -d --build
curl http://127.0.0.1:8090/api/health
```

## DF100M Reverse Engineering

**DE:** UUIDs und Begriffe wie `wind_set_speed` sind Reverse-Engineering-Anhaltspunkte aus der Legacy-App-Analyse und keine offizielle Mars-Hydro-Protokolldokumentation.

**EN:** UUIDs and strings such as `wind_set_speed` are reverse-engineering evidence from Legacy app analysis and are not official Mars Hydro protocol documentation.

Darum / Therefore:

```text
DF100M_ALLOW_WRITES=false
```

bleibt der sichere Standard / remains the safe default.

- [DE: Protokollanalyse](docs/de/DF100M_PROTOCOL.md)
- [EN: Protocol research](docs/en/DF100M_PROTOCOL.md)

## Code-Dokumentation / Code Documentation

**DE:** Kern-Code und Deployment-Dateien enthalten zweisprachige Kommentare zu Zweck, Datenfluss, Sicherheitsgrenzen und experimentellen Funktionen.

**EN:** Core code and deployment files contain bilingual comments explaining purpose, data flow, security boundaries and experimental behavior.

## Quellen / Sources

Herstellerinformationen, Open-Source-Inspiration, APK-Beobachtungen und experimentelle Annahmen werden getrennt dokumentiert.

Vendor information, open-source inspiration, APK observations and experimental assumptions are documented separately.

Siehe / See: [docs/SOURCES.md](docs/SOURCES.md)

## Lizenz / License

MIT.

Mars Hydro, DF100M und Mars Legacy sind Produkt-/Markenbezeichnungen Dritter.  
Mars Hydro, DF100M and Mars Legacy are third-party product/trademark names.

135er GrowControl ist ein unabhängiges Projekt.  
135er GrowControl is an independent project.
