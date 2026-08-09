# 135er GrowControl

> Local-first Raspberry-Pi control, monitoring and automation platform with an optional Linux VPS cloud layer.

**Project owner / initiator:** JensJenzo  
**Primary target:** Raspberry Pi 3B/3B+ and newer Raspberry Pi systems  
**Current device focus:** Mars Hydro DF100M / MZ_MZF002  
**Architecture principle:** Raspberry Pi is always the local master. Cloud is optional.  
**ESP32:** not required and intentionally excluded from the core architecture.

![Version](https://img.shields.io/badge/version-0.5.x%20hardware--test-35f0a7)
![Platform](https://img.shields.io/badge/platform-Raspberry%20Pi%20%7C%20Debian%20%7C%20Ubuntu-c51a4a)
![Architecture](https://img.shields.io/badge/architecture-local--first-32ccff)
![Docs](https://img.shields.io/badge/docs-DE%20%7C%20EN-8e6cff)
![License](https://img.shields.io/badge/license-MIT-blue)

## Vision

135er GrowControl entstand aus der Idee, Smart-Grow-Hardware ohne dauerhafte Abhängigkeit von einer Hersteller-App lokal über einen Raspberry Pi zu überwachen und später sicher zu steuern. Aus dem ersten DF100M-BLE-Testprojekt wurde schrittweise eine Plattformidee: lokale Geräteadapter, Sensorik, Historie, Zeitpläne, Automationen, Benutzer/Rollen, Audit-Logging, optionale Cloud-Synchronisation und ein responsives Web-HUD.

Das Projekt verfolgt ausdrücklich **keinen Cloud-Zwang**. Ein Ausfall von Internet oder VPS darf lokale Funktionen nicht blockieren.

## Aktueller Stand

| Bereich | Status |
|---|---|
| Raspberry-Pi-/FastAPI-Laufzeit | ✅ vorhanden |
| BLE Discovery | ✅ implementiert |
| Connect / Disconnect | ✅ implementiert |
| GATT Inspection | ✅ implementiert |
| Notification Capture | 🧪 experimentell |
| DF100M Speed Protocol | 🧪 noch nicht validiert |
| Lokale Web-GUI | ✅ technische Basis / 🎨 Zielbild definiert |
| Responsive HUD-Design | ✅ Referenz definiert |
| Cloud Telemetry | 🧪 Alpha |
| Cloud History | 🧪 Alpha |
| Remote Commands | 🔒 vorbereitet, standardmäßig deaktiviert |
| SQLite lokal | ✅ Baseline |
| PostgreSQL Cloud | 🧱 Schema-/Plattformziel |
| RBAC / Benutzer / Rollen | 🧱 Datenmodell und Rechtekonzept definiert |
| Sensoren / Historie | 🧱 Plattformmodell definiert |
| Zeitpläne / Automationen | 🧱 Plattformmodell definiert |
| Pi-3B-Testimage | 🔧 GitHub-Actions-Build in Entwicklung |
| Erste reale DF100M-Hardwaretests | ⏭️ nächster Meilenstein |

Legende: ✅ implementiert · 🧪 experimentell/Alpha · 🧱 Baseline/Design vorhanden, Runtime noch nicht vollständig verdrahtet · 🔒 sicher vorbereitet · 🔧 in Arbeit · ⏭️ nächster Schritt.

## Architektur

```text
Browser / iPad / Smartphone
          │
          ▼
135er GrowControl Local
Raspberry Pi ────────────── outbound HTTPS ─────────────► Linux VPS
    │                                                  GrowControl Cloud
    │ BLE                                               │
    ▼                                                   ├─ Telemetry
  DF100M                                                ├─ History
                                                        └─ Remote overview
```

### Sicherheitsgrenzen

- Der Raspberry Pi bleibt Master.
- Port 8080 wird nicht direkt ins öffentliche Internet exponiert.
- Cloud-Kommunikation erfolgt vom Pi ausgehend über HTTPS.
- Remote Commands benötigen explizite Freigabe und lokale Validierung.
- `DF100M_ALLOW_WRITES=false` bleibt Standard, bis das Protokoll am realen Gerät validiert ist.
- Test-Zugangsdaten `test/test` sind ausschließlich für das aktuelle Hardware-Testimage vorgesehen.

## GUI-Zielbild

![135er GrowControl GUI Preview](docs/assets/gui/gui-preview-v0.5.png)

Die Vorschau ist die Designreferenz für Desktop, Notebook, Tablet/iPad und Smartphone. Technische Breakpoints und UX-Regeln stehen in der GUI-Dokumentation.

## Projektwissen / Project Record

Die vollständige Entwicklung von der ersten Idee bis zum aktuellen Hardware-Teststand ist dokumentiert:

- [Projektgeschichte / Project history](PROJECT_HISTORY.md)
- [Aktueller Projektstatus](docs/PROJECT_STATUS.md)
- [Architektur-Master](docs/ARCHITECTURE_MASTER.md)
- [DF100M Research Log](docs/DF100M_RESEARCH_LOG.md)
- [Hardware-Testplan](docs/HARDWARE_TEST_PLAN.md)
- [Security & Trust Model](docs/SECURITY_AND_TRUST_MODEL.md)
- [Image- & Release-Prozess](docs/RELEASE_AND_IMAGE_PROCESS.md)
- [Entscheidungslog](docs/DECISION_LOG.md)
- [Bekannte Grenzen](docs/KNOWN_LIMITATIONS.md)
- [Changelog](CHANGELOG.md)
- [Roadmap](docs/ROADMAP.md)
- [Quellen](docs/SOURCES.md)

## Dokumentation

- 🇩🇪 [Deutsch](docs/de/README.md)
- 🇬🇧 [English](docs/en/README.md)
- 📚 [Dokumentationsindex](docs/README.md)
- 📖 [Wiki-Quelle](wiki/Home.md)

Die `wiki/`-Struktur ist die versionierte kanonische Quelle für ein GitHub-Wiki-Mirroring.

## Raspberry Pi Quick Start

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

Aufruf im lokalen Netz:

```text
http://PI-IP:8080
```

## DF100M – bestätigte und beobachtete Daten

Aktuelles Testgerät:

```text
Legacy identifier: MZ_MZF002_0_A0A3B35EFDC8
Device ID:         A0A3B35EFDC8
Firmware:          V1.8
```

Beobachtete Legacy-App-Begriffe umfassen u. a. `wind_speed`, `wind_set_speed`, `RPM`, `discoverServices`, `writeCharacteristicWithResponse` und `NotifyCharacteristicRequest`.

Kandidaten-UUIDs:

```text
6f588463-f8f1-44f8-bdae-a1272a1b0f6e
83677baa-3eb8-4866-b6b6-96e5ed5cc48d
f5d2b3fe-e6b5-49b5-aa5f-a00bb4156d1d
```

Diese Angaben sind **Reverse-Engineering-Beobachtungen und keine offizielle Mars-Hydro-Protokolldokumentation**.

## API – lokale Basis

Bekannte Endpunkte der aktuellen lokalen FastAPI-Basis:

```text
GET  /api/health
GET  /api/config
GET  /api/status
GET  /api/discover
POST /api/connect
POST /api/disconnect
GET  /api/services
POST /api/notify/start
POST /api/notify/stop
POST /api/speed
POST /api/raw
```

Experimentelle Schreibpfade bleiben standardmäßig deaktiviert.

## Cloud – aktuelle Alpha-Basis

```text
GET  /api/health
POST /api/v1/telemetry
GET  /api/v1/sites/{site_id}/latest
GET  /api/v1/sites/{site_id}/history
POST /api/v1/commands
GET  /api/v1/sites/{site_id}/commands/pending
POST /api/v1/commands/{command_id}/result
```

Aktuelle Alpha-Authentisierung verwendet einen statischen `X-API-Token`. Das Zielbild sieht Benutzer, Sessions und RBAC vor; dies darf nicht mit einer bereits vollständig produktiven Auth-Laufzeit verwechselt werden.

## Unterstützte Plattformziele

- Raspberry Pi OS 64-bit / Debian-basiert
- Debian 12 / 13
- Ubuntu Server 22.04 / 24.04 LTS
- systemd
- APT / unattended-upgrades
- Nginx / HTTPS für Serverbetrieb
- Firewall / Fail2ban als Plattformbaseline

## Lizenz und Unabhängigkeit

MIT. Mars Hydro, DF100M und Mars Legacy sind Marken-/Produktbezeichnungen Dritter. 135er GrowControl ist ein unabhängiges Open-Source-Projekt und keine offizielle Mars-Hydro-Software.
