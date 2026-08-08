# 135er GrowControl

> **Lokale Raspberry-Pi-Steuerplattform für Mars-Hydro-Smart-Geräte**  
> Aktueller Testfokus: **Mars Hydro DF100M / MZ_MZF002**

![Status](https://img.shields.io/badge/status-early%20test-orange)
![Version](https://img.shields.io/badge/version-0.3.2-35f0a7)
![Platform](https://img.shields.io/badge/platform-Raspberry%20Pi-c51a4a)
![Python](https://img.shields.io/badge/backend-Python%20%2F%20FastAPI-32ccff)
![BLE](https://img.shields.io/badge/device-Bluetooth%20LE-8e6cff)
![ESP32](https://img.shields.io/badge/ESP32-not%20required-35f0a7)
![License](https://img.shields.io/badge/license-MIT-blue)

---

## Was ist 135er GrowControl?

**135er GrowControl** ist eine lokale, modulare Steuer- und Überwachungsplattform für einen Raspberry Pi.

Das Projekt verfolgt das Ziel, kompatible Smart-Geräte nicht dauerhaft über mehrere Hersteller-Apps bedienen zu müssen, sondern sie in einer **zentralen lokalen Weboberfläche** zusammenzuführen.

Der erste untersuchte Gerätetyp ist der:

```text
Mars Hydro DF100M
Gerätefamilie: MZ_MZF002
beobachtete Firmware: V1.8
```

Der Raspberry Pi übernimmt dabei die komplette Steuerzentrale.

**Es wird kein ESP32 benötigt.**

---

## Projektidee

Die geplante Architektur:

```text
                         ┌──────────────────────┐
                         │   iPad / Browser     │
                         │                      │
                         │  135er GrowControl   │
                         └──────────┬───────────┘
                                    │
                             HTTP / WebSocket
                                    │
                                    ▼
                    ┌───────────────────────────┐
                    │       Raspberry Pi        │
                    │                           │
                    │        FastAPI Core       │
                    │                           │
                    │   ┌───────────────────┐   │
                    │   │ Device Registry   │   │
                    │   │ Automation Engine │   │
                    │   │ Event Logging     │   │
                    │   │ SQLite            │   │
                    │   │ MQTT optional     │   │
                    │   └─────────┬─────────┘   │
                    └─────────────┼─────────────┘
                                  │
                          Device Adapter
                                  │
                     ┌────────────┴────────────┐
                     │                         │
                    BLE                  zukünftige
                     │                    Adapter
                     ▼                         │
             ┌──────────────┐         ┌───────┴───────┐
             │    DF100M    │         │ FC3000        │
             │   MZF002     │         │ Sensoren      │
             └──────────────┘         │ weitere Geräte│
                                      └───────────────┘
```

---

# Funktionsumfang

## Bereits vorhanden

Die aktuelle Testversion beinhaltet:

### Webinterface

- futuristisches HUD-Design
- responsive Darstellung
- Desktop-Unterstützung
- iPad-/Tablet-Optimierung
- Geräteübersicht
- DF100M-Steuerbereich
- BLE-Diagnosekonsole
- Systemübersicht
- vorbereitete Navigation für:
  - Dashboard
  - Geräte
  - Automation
  - Historie
  - System

### Raspberry-Pi-Backend

Das Backend basiert auf:

```text
Python
FastAPI
Uvicorn
Bleak
SQLite
```

Der Raspberry Pi stellt Webinterface und API bereit.

### Bluetooth LE

Aktuell implementiert:

- BLE-Gerätesuche
- Filterung nach Mars-/MZF-Geräten
- Verbindung mit einem gefundenen Gerät
- Trennen der Verbindung
- GATT-Service-Ausgabe
- Characteristic-Properties anzeigen
- Vorbereitung für Notifications
- experimenteller Command-Endpunkt

### Datenhaltung

SQLite ist als lokale Datenbank vorgesehen für:

- Ereignisse
- Geräteinformationen
- spätere Messwerte
- Fehler
- Automationsereignisse

### Systembetrieb

Enthalten ist eine vorbereitete `systemd`-Unit.

Damit kann GrowControl später beim Start des Raspberry Pi automatisch gestartet werden.

---

# Aktueller DF100M-Status

Der aktuelle Entwicklungsstand:

```text
BLE Discovery           ██████████   vorhanden
BLE Connection          ██████████   vorhanden
GATT Inspection         ██████████   vorhanden

DF100M Identification   ████████░░   weit fortgeschritten

Notifications           ████░░░░░░   Analysephase
Status Decoder          ███░░░░░░░   Analysephase
Fan Speed Command       ███░░░░░░░   experimentell

Automation              ██░░░░░░░░   vorbereitet
Historie                 ██░░░░░░░░   vorbereitet
FC3000                   ░░░░░░░░░░   später
```

---

# Reverse Engineering des DF100M

Mars Hydro veröffentlicht für den DF100M derzeit keine vollständige offene BLE-Protokollbeschreibung.

Daher wird die Kommunikation schrittweise analysiert.

Aus der im Projekt untersuchten **Mars Legacy 1.2.2 APK** wurden unter anderem folgende technische Strings identifiziert:

```text
MZ_MZF
MZ_MZF002
Fan type
Wind Speed

wind_speed
wind_speed_num
wind_set_speed
wind_save_enable

RPM

flutter_reactive_ble

discoverServices
writeCharacteristicWithResponse
NotifyCharacteristicRequest
```

Diese Informationen liefern Hinweise auf die interne Kommunikation.

---

## Gefundene UUID-Kandidaten

Im Analysekontext wurden folgende UUIDs gefunden:

```text
6f588463-f8f1-44f8-bdae-a1272a1b0f6e

83677baa-3eb8-4866-b6b6-96e5ed5cc48d

f5d2b3fe-e6b5-49b5-aa5f-a00bb4156d1d
```

### Wichtig

Diese UUIDs gelten momentan als:

> **Reverse-Engineering-Kandidaten**

Noch nicht vollständig bestätigt sind:

- welche UUID ein Service ist
- welche Characteristic gelesen wird
- welche Characteristic geschrieben wird
- welche Characteristic Notifications liefert
- das exakte Fan-Speed-Payload
- mögliche Header
- Checksummen
- Initialisierungssequenzen
- Statusframes

Deshalb werden experimentelle Funktionen im Projekt auch entsprechend gekennzeichnet.

---

# Geplanter DF100M-Test

Der Test erfolgt schrittweise.

## 1. Gerät suchen

Im Webinterface:

```text
DISCOVER
```

GrowControl startet einen BLE-Scan.

Gesucht werden insbesondere Geräte mit Bezeichnungen wie:

```text
MZ_MZF002
MZF
Mars
```

---

## 2. Verbindung herstellen

Nach erfolgreicher Suche verbindet sich GrowControl über Bluetooth LE mit dem Gerät.

---

## 3. GATT auslesen

Über:

```text
READ GATT
```

werden Services und Characteristics ausgegeben.

Beispiel:

```text
Service
 ├─ Characteristic
 │   ├─ read
 │   ├─ write
 │   └─ notify
 │
 └─ Characteristic
     └─ write-with-response
```

Damit kann die tatsächliche Struktur des DF100M mit den APK-Funden verglichen werden.

---

## 4. Mars Legacy vergleichen

In einem späteren Protokolltest werden definierte Lüfterwerte in Mars Legacy gesetzt.

Beispielsweise:

```text
10 %
30 %
50 %
70 %
90 %
```

Die dabei übertragenen BLE-Daten können miteinander verglichen werden.

---

## 5. Payload rekonstruieren

Zu untersuchen sind unter anderem:

```text
Prozentwert
Fan-Stufe
Byte-Reihenfolge
Command Header
Device ID
Checksumme
Counter
Response
Notification
```

---

## 6. Raspberry-Pi-Replay

Erst wenn das Paket reproduzierbar verstanden wurde, wird derselbe Befehl direkt vom Raspberry Pi gesendet.

Dann kann der DF100M vollständig in GrowControl integriert werden.

---

# Geplante Automatisierung

Nach erfolgreicher DF100M-Integration soll GrowControl selbständig regeln können.

Beispiel:

```text
Temperatur steigt
       │
       ▼
Automationslogik
       │
       ▼
DF100M Zielwert erhöhen
       │
       ▼
Temperatur fällt
       │
       ▼
Lüfter schrittweise reduzieren
```

Dabei sollen unter anderem berücksichtigt werden:

- Temperatur
- Luftfeuchtigkeit
- VPD
- Hysterese
- Mindestlaufzeit
- Mindeständerung
- Zeitpläne
- Nachtmodus
- manuelle Übersteuerung
- Sensorfehler
- Verbindungsfehler

---

# Zukünftige Geräte

Die Architektur ist bewusst modular.

Geplant bzw. denkbar:

## Mars Hydro FC3000

Spätere Funktionen:

- Ein/Aus
- Dimmung
- Zeitplan
- Gerätegesundheit
- Automationsintegration

## Klimasensoren

Mögliche Werte:

```text
Temperatur
Luftfeuchtigkeit
VPD
Taupunkt
```

## Weitere Geräte

Geräte sollen über Adapter eingebunden werden:

```text
app/devices/
    df100m/
    fc3000/
    sensors/
    ...
```

Die Weboberfläche muss dadurch keine gerätespezifischen BLE-Kommandos kennen.

---

# Webinterface

Das Interface verfolgt einen technischen **Future-HUD-Stil**.

Aktuelle Bereiche:

```text
Dashboard
├── Temperatur
├── Luftfeuchtigkeit
├── Lüfterstatus
├── Protokollstatus
├── Lüfterregler
└── BLE-Diagnose

Geräte
├── DF100M
├── FC3000 (geplant)
└── Sensorik (geplant)

Automation
Historie
System
```

Das Interface ist speziell so aufgebaut, dass es dauerhaft auf einem Tablet oder iPad angezeigt werden kann.

---

# Technischer Stack

## Backend

```text
Python
FastAPI
Uvicorn
Pydantic
```

## Bluetooth

```text
Bleak
BlueZ
```

## Datenbank

```text
SQLite
aiosqlite
```

## Frontend

```text
HTML5
CSS
JavaScript
REST API
```

Später vorgesehen:

```text
WebSocket
MQTT
Charts
Live Telemetry
```

---

# Projektstruktur

```text
135er_GrowControl/
│
├── app/
│   ├── api/
│   │   └── routes.py
│   │
│   ├── core/
│   │   └── config.py
│   │
│   ├── db/
│   │   └── database.py
│   │
│   └── devices/
│       └── df100m/
│           ├── adapter.py
│           └── protocol.py
│
├── web/
│   ├── index.html
│   ├── app.css
│   └── app.js
│
├── docs/
│   ├── ARCHITECTURE.md
│   ├── API.md
│   ├── DF100M_PROTOCOL.md
│   ├── INSTALLATION.md
│   ├── ROADMAP.md
│   ├── SOURCES.md
│   └── TROUBLESHOOTING.md
│
├── systemd/
│   └── 135er-growcontrol.service
│
├── tests/
│
├── .github/
│   ├── workflows/
│   └── ISSUE_TEMPLATE/
│
├── requirements.txt
├── project.json
├── SECURITY.md
├── CONTRIBUTING.md
├── CHANGELOG.md
├── LICENSE
└── README.md
```

---

# Installation auf dem Raspberry Pi

Empfohlen:

- Raspberry Pi 4 oder 5
- Raspberry Pi OS 64-bit
- Bluetooth LE
- Python 3.11 oder neuer
- Ethernet oder WLAN

## Pakete installieren

```bash
sudo apt update

sudo apt install -y     git     python3     python3-pip     python3-venv     bluetooth     bluez
```

---

## Projekt laden

Nach einem GitHub-Upload beispielsweise:

```bash
git clone https://github.com/DEINNAME/135er-GrowControl.git

cd 135er-GrowControl
```

---

## Python-Umgebung

```bash
python3 -m venv .venv

source .venv/bin/activate

pip install --upgrade pip

pip install -r requirements.txt
```

Konfiguration kopieren:

```bash
cp .env.example .env
```

---

# GrowControl starten

```bash
uvicorn app.main:app     --host 0.0.0.0     --port 8080
```

Danach im Browser:

```text
http://RASPBERRY-PI-IP:8080
```

Beispiel:

```text
http://192.168.178.50:8080
```

---

# API

## Systemstatus

```http
GET /api/health
```

---

## DF100M Status

```http
GET /api/df100m/status
```

---

## BLE-Suche

```http
GET /api/df100m/discover
```

---

## Verbindung

```http
POST /api/df100m/connect?address=BLE-ADDRESS
```

---

## GATT

```http
GET /api/df100m/services
```

---

## Experimenteller Speed-Test

```http
POST /api/df100m/speed?percent=30
```

Der Speed-Endpunkt ist in dieser Entwicklungsphase ausdrücklich experimentell.

---

# Sicherheit

GrowControl ist momentan für den Betrieb im **lokalen Netzwerk** vorgesehen.

Port `8080` sollte nicht direkt aus dem Internet erreichbar sein.

Für externen Zugriff später beispielsweise:

```text
WireGuard
Tailscale
Reverse Proxy
HTTPS
Authentication
```

Keine vertraulichen Daten committen:

```text
.env
API Tokens
Passwörter
Private Keys
Session Tokens
```

Siehe:

[`SECURITY.md`](SECURITY.md)

---

# Roadmap

## v0.3.x

- BLE Discovery
- GATT Inspection
- Future UI
- Dokumentation
- Raspberry-Pi-Testplattform

## v0.4

- DF100M Characteristic Mapping
- Notification Capture
- Speed Protocol
- Status Decoder
- Reconnect

## v0.5

- Live Telemetry
- WebSocket
- Messwerthistorie
- Charts
- Device Health

## v0.6

- Automation Engine
- Temperaturregelung
- Feuchteregelung
- VPD
- Hysterese
- Zeitpläne

## v0.7+

- FC3000
- externe Sensoren
- MQTT
- Home Assistant
- Backup
- Benutzerverwaltung
- Update-System

Ausführlich:

[`docs/ROADMAP.md`](docs/ROADMAP.md)

---

# Inspiration

Eine wichtige Open-Source-Referenz für das Grundkonzept war:

**KillerInk / GrowFanController**

https://github.com/KillerInk/GrowFanController

Das Projekt kombiniert unter anderem:

- Lüftersteuerung
- Sensorik
- VPD
- Licht
- Automatisierung
- Logging
- Webinterface

Der wesentliche Unterschied:

> GrowFanController nutzt einen ESP32.  
> **135er GrowControl verlagert die komplette Control-Plane auf den Raspberry Pi.**

---

# Quellen und Referenzen

## Mars Hydro – offizielle Quellen

Mars Hydro Smart-App:

https://www.mars-hydro.com/mars-hydro-app

Mars Hydro Smart Grow FAQ:

https://www.mars-hydro.com/info/post/faqs-about-the-mars-hydro-app-and-smart-grow-system

Mars Hydro Inline Fan FAQ:

https://www.mars-hydro.com/faq/inline-fan

Mars Hydro iControl Technical Guide:

https://www.mars-hydro.com/intelligent-icontrol-system-technical-guide

---

## Mars Legacy

Google Play:

https://play.google.com/store/apps/details?id=com.mz.mziot

Paket:

```text
com.mz.mziot
```

---

## Projektinterne Analyse

Für das Projekt wurde eine bereitgestellte Version von:

```text
Mars Legacy 1.2.2
```

untersucht.

Die daraus gewonnenen BLE-/MZF-Bezeichnungen werden im Projekt ausdrücklich als:

```text
APK-OBSERVATION
```

bzw.

```text
EXPERIMENTAL
```

gekennzeichnet.

Eine vollständige Übersicht mit Einordnung befindet sich in:

[`docs/SOURCES.md`](docs/SOURCES.md)

---

# Haftung / Projektstatus

135er GrowControl ist derzeit ein **experimentelles Community-/Reverse-Engineering-Projekt**.

Es besteht keine Verbindung oder Partnerschaft mit Mars Hydro.

Mars Hydro, DF100M, Mars Legacy und weitere Produktnamen sind Marken bzw. Produktbezeichnungen ihrer jeweiligen Rechteinhaber.

Die Software wird ohne Gewähr bereitgestellt.

---

# Lizenz

Der eigene Projektcode steht unter der **MIT License**.

Siehe:

[`LICENSE`](LICENSE)

---

## Kurz gesagt

135er GrowControl soll aus:

```text
einzelnen Smart-Geräten
+
Hersteller-Apps
+
Sensoren
```

eine zentrale lokale Plattform machen:

```text
             135er GrowControl
                    │
      ┌─────────────┼─────────────┐
      │             │             │
    DF100M        FC3000       Sensoren
      │             │             │
      └─────────────┼─────────────┘
                    │
              Raspberry Pi
                    │
                    ▼
             iPad / Browser
```

**Local-first. Modular. Erweiterbar. Ohne ESP32.**
