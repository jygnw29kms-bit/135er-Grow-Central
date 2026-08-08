# 135er GrowControl

**DE:** Local-First Raspberry-Pi-Steuerplattform mit optionaler Linux-VServer-Cloud.  
**EN:** Local-first Raspberry Pi control platform with an optional Linux VPS cloud layer.

Aktueller Gerätefokus / Current device focus: **Mars Hydro DF100M / MZ_MZF002**  
**Kein ESP32 erforderlich / No ESP32 required**

![Version](https://img.shields.io/badge/version-0.4.1-35f0a7)
![Platform](https://img.shields.io/badge/platform-Raspberry%20Pi-c51a4a)
![Cloud](https://img.shields.io/badge/cloud-optional-32ccff)
![Docs](https://img.shields.io/badge/docs-DE%20%7C%20EN-8e6cff)
![License](https://img.shields.io/badge/license-MIT-blue)

## Dokumentation / Documentation

- 🇩🇪 [Deutsch](docs/de/README.md)
- 🇬🇧 [English](docs/en/README.md)
- 📚 [Dokumentationsindex / Documentation index](docs/README.md)
- 🔎 [Quellen / Sources](docs/SOURCES.md)

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

## Status

| Bereich / Area | Status |
|---|---|
| BLE Discovery | ✅ implemented |
| BLE Connect / Disconnect | ✅ implemented |
| GATT Inspection | ✅ implemented |
| Notification Capture | 🧪 experimental |
| DF100M Speed Protocol | 🧪 not validated |
| Future HUD | ✅ available |
| Cloud Telemetry | 🧪 alpha |
| Cloud History | 🧪 alpha |
| Remote Commands | 🔒 prepared, disabled by default |
| FC3000 Adapter | 🗺️ planned |
| Sensor / VPD Automation | 🗺️ planned |

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
