# 135er GrowControl

<p align="center">
  <img src="website/assets/brand/135er-growcontrol-repo-mark.png" alt="135er GrowControl Logo" width="210">
</p>

<p align="center">
  <strong>LOCAL-FIRST · RASPBERRY PI · SMART HOME · POWER TELEMETRY</strong>
</p>

<p align="center">
  <code>🚧 WORK IN PROGRESS</code>
  &nbsp; <code>v0.7 development</code>
  &nbsp; <code>Raspberry Pi master</code>
  &nbsp; <code>deny-by-default writes</code>
</p>

> [!WARNING]
> **Work in Progress:** 135er GrowControl befindet sich aktiv in Entwicklung. Architektur, GUI und Smart-Home-Baselines sind bereits vorhanden, einzelne Hardware-/Protokollpfade – insbesondere DF100M – sind noch experimentell und nicht als vollständig validierte Produktionsunterstützung zu verstehen.

<p align="center">
  <img src="docs/assets/gui/gui-preview-v0.5.png" alt="135er GrowControl GUI reference" width="900">
</p>

## Control Plane

| Bereich | Ziel / Status |
|---|---|
| **Local Master** | Raspberry Pi bleibt authoritative controller |
| **Frontend** | Responsive HUD für Desktop, iPad und Smartphone |
| **Power** | Smart-Plug Status, W, kWh, V, A, Hz und Kostenhochrechnung |
| **Smart Home** | Shelly direkt; Home Assistant als optionale Bridge |
| **Cloud** | Optional, niemals Voraussetzung für lokale Steuerung |
| **Security** | Inventory → Approval → Writable → Authenticated command |
| **Project status** | **WORK IN PROGRESS** |

135er GrowControl ist eine modulare, lokale Automationsplattform für Klima-, Geräte- und Energiedaten. Der Raspberry Pi bleibt die Steuerzentrale. Externe Dienste und Cloud-Funktionen sind optionale Erweiterungen und dürfen den lokalen Betrieb nicht zum Single Point of Failure machen.

## Architektur

```text
Apple Home / Siri      FRITZ! / Tapo / weitere Ökosysteme
        \                         /
         \                       /
          +---- Home Assistant --+     optional bridge
                    |
                    | REST
                    v
           135er GrowControl Local
              Raspberry Pi
              /    |      \
             /     |       \
        BLE DF100M |        Shelly Gen2+ RPC
                    |
                 SQLite
                    |
             outbound HTTPS
                    v
              optional cloud
```

## Integrationen

| Integration | Strategie | Aktueller Stand |
|---|---|---|
| Mars Hydro DF100M | BLE / kontrolliertes Reverse Engineering | Experimentelle Hardwarevalidierung |
| Shelly Gen2+ | Direkter lokaler JSON-RPC | Adapter-Baseline implementiert |
| Home Assistant | Lokaler REST-Connector | Adapter-Baseline implementiert |
| TP-Link Tapo | Via Home Assistant | Architekturpfad definiert |
| FRITZ!SmartHome / FRITZ!DECT | Via Home Assistant | Architekturpfad definiert |
| Apple Home / Siri | Home Assistant HomeKit Bridge | Architekturpfad definiert |
| Matter | Standards-basierter Bridge-Pfad | Geplant |

## Sicherheitsdefaults

```text
DF100M_ALLOW_WRITES=false
GC_REMOTE_COMMANDS=false
GC_CLOUD_ENABLED=false
GC_SMARTHOME_ENABLED=false
GC_HA_READ_ONLY=true
GC_LOCAL_API_TOKEN=
```

Ohne konfiguriertes `GC_LOCAL_API_TOKEN` verweigern geschützte Write-Endpunkte Steuerbefehle.

## Repository Map

```text
app/                 Local FastAPI runtime
app/smarthome/       Registry, policy and adapters
web/                 Local Raspberry-Pi HUD
website/             Public static project website
database/            Local/cloud schema baselines
cloud/               Optional cloud alpha
docs/                Canonical technical documentation
wiki/                Versioned wiki source
image-builder/       Raspberry Pi image pipeline
```

## Branding

Für sichtbare Web-/Repository-Grafiken werden **PNG/ICO** verwendet. WebP wird aufgrund der festgestellten Darstellungsprobleme im produktiven Hosting nicht mehr eingesetzt.

- Logo: `website/assets/brand/135er-growcontrol-repo-mark.png`
- Favicon: `website/assets/brand/favicon.ico`
- GUI-Referenz: `docs/assets/gui/gui-preview-v0.5.png`
- Regeln: [`BRANDING.md`](BRANDING.md)

## Dokumentation

- [`docs/PROJECT_STATUS.md`](docs/PROJECT_STATUS.md) – verbindlicher Implementierungsstatus
- [`docs/ARCHITECTURE_MASTER.md`](docs/ARCHITECTURE_MASTER.md) – Systemarchitektur
- [`docs/SMART_HOME_ARCHITECTURE.md`](docs/SMART_HOME_ARCHITECTURE.md) – Smart-Home-Architektur
- [`docs/INTEGRATIONS.md`](docs/INTEGRATIONS.md) – Integrationsstrategie
- [`docs/SECURITY_AND_TRUST_MODEL.md`](docs/SECURITY_AND_TRUST_MODEL.md) – Sicherheitsgrenzen
- [`docs/HARDWARE_TEST_PLAN.md`](docs/HARDWARE_TEST_PLAN.md) – DF100M-Validierung
- [`PROJECT_HISTORY.md`](PROJECT_HISTORY.md) – Projektgeschichte
- [`website/README.md`](website/README.md) – öffentliche Website und Deployment

## English status note

**135er GrowControl is an active work in progress.** The repository already contains working architecture and adapter baselines, but experimental hardware paths must not be interpreted as fully validated production support. The Raspberry Pi remains the authoritative local master and protected writes stay deny-by-default.
