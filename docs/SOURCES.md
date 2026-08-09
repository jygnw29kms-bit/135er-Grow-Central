# Quellen, Referenzen und Herkunft der technischen Informationen

Stand: August 2026

135er-Grow Central unterscheidet ausdrücklich zwischen:

1. **offiziellen Herstellerinformationen**
2. **öffentlichen Open-Source-Referenzen**
3. **eigenen Reverse-Engineering-Beobachtungen**
4. **noch nicht validierten technischen Annahmen**

Diese Trennung ist wichtig, weil die DF100M-BLE-Kommandostruktur noch nicht vollständig dokumentiert ist.

---

## 1. Offizielle Mars-Hydro-Quellen

### Mars Hydro App / Smart Grow System

Mars Hydro beschreibt seine Smart-Grow-Plattform als System zur Steuerung von Smart-Lights und Smart-Inline-Fans über Wi-Fi bzw. Bluetooth. Laut Hersteller können Geräte ein- und ausgeschaltet sowie Helligkeit bzw. Lüftergeschwindigkeit eingestellt werden.

Quelle:

https://www.mars-hydro.com/mars-hydro-app

Verwendung im Projekt:

- Bestätigung, dass Mars-Hydro-Smart-Fans App-gesteuerte Geschwindigkeitsregelung unterstützen.
- Hintergrund für die geplante lokale Geräteabstraktion.

### Mars Hydro Smart Grow FAQ

Mars Hydro nennt BLE ausdrücklich als Voraussetzung für die Bluetooth-Verbindung kompatibler Geräte.

Quelle:

https://www.mars-hydro.com/info/post/faqs-about-the-mars-hydro-app-and-smart-grow-system

Verwendung im Projekt:

- Bestätigung der BLE-Kommunikation im offiziellen Smart-System.
- Grundlage für Raspberry-Pi-BLE als primären Untersuchungsweg.

### Mars Hydro Inline Fan FAQ

Mars Hydro dokumentiert bei Smart-/Controller-Lösungen manuell einstellbare Lüftergeschwindigkeiten und temperatur-/feuchteabhängige Regelstrategien.

Quelle:

https://www.mars-hydro.com/faq/inline-fan

Verwendung im Projekt:

- Referenz für mögliche zukünftige Automationsfunktionen.

### Mars Hydro iControl Technical Guide

Der aktuelle Herstellerleitfaden beschreibt Fan-Modi wie Manual, Timer, Cycle und Environmental Mode sowie regelbare Lüftergeschwindigkeit.

Quelle:

https://www.mars-hydro.com/intelligent-icontrol-system-technical-guide

Hinweis:

Diese Quelle beschreibt das aktuelle iControl/iFresh-Ökosystem und **nicht zwingend das ältere DF100M-Legacy-Protokoll**. Sie wird daher nur als funktionale Referenz verwendet.

---

## 2. Mars Legacy

### Google Play – Mars Legacy

Paket:

`com.mz.mziot`

Quelle:

https://play.google.com/store/apps/details?id=com.mz.mziot

Google Play beschreibt Mars Legacy als Anwendung zur Verwaltung und Steuerung lokaler Geräte. Als unterstützte Gerätekategorien werden unter anderem Lichter, Ventilatoren sowie Temperatur- und Feuchtigkeitssensoren genannt.

Verwendung im Projekt:

- Referenz für das ältere Mars-Hydro-Geräteökosystem.
- Bestätigung, dass die Legacy-App Fan- und Sensorgeräte verwaltet.
- Grundlage der APK-Untersuchung.

---

## 3. Open-Source-Referenz

### KillerInk / GrowFanController

Repository:

https://github.com/KillerInk/GrowFanController

Das Projekt ist ein ESP32-basierter Klima-Controller mit:

- Fan-Control
- automatischer Regelung
- Lichtsteuerung
- Sensorüberwachung
- VPD
- Datenlogging
- Web-Dashboard
- WebSocket-Livedaten

135er-Grow Central nutzt diese Ideen **nur als Architektur- und UI-Inspiration**.

Wesentlicher Unterschied:

> 135er-Grow Central verwendet keinen ESP32 als Hauptcontroller.

Stattdessen übernimmt der Raspberry Pi:

- Gerätekommunikation
- Webserver
- Automationslogik
- Logging
- MQTT
- zukünftige Sensorintegration

---

## 4. Eigene Reverse-Engineering-Beobachtungen

Für das Projekt wurde die vom Benutzer bereitgestellte Datei

`Mars Legacy 1.2.2`

untersucht.

In den analysierten App-Bestandteilen wurden unter anderem folgende Strings bzw. technische Bezeichnungen gefunden:

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

Außerdem wurden im Analysekontext folgende UUID-Kandidaten identifiziert:

```text
6f588463-f8f1-44f8-bdae-a1272a1b0f6e
83677baa-3eb8-4866-b6b6-96e5ed5cc48d
f5d2b3fe-e6b5-49b5-aa5f-a00bb4156d1d
```

Diese Informationen stammen **nicht aus einer offiziellen Mars-Hydro-Protokolldokumentation**.

Sie sind Reverse-Engineering-Anhaltspunkte.

---

## 5. Noch nicht bestätigte Punkte

Derzeit noch experimentell:

- exakte Zuordnung der drei UUIDs
- Service vs. Characteristic
- Read / Write / Notify
- DF100M-Speed-Payload
- Paket-Header
- Checksummen
- mögliche Initialisierungssequenz
- Zuordnung 0–100 % zu internen Fan-Stufen
- vollständige Statusdekodierung

Darum kennzeichnet die Software diese Funktionen als Test-/Experimentalbereiche.

---

## 6. Zitierweise im Repository

In Dokumentationen sollten Behauptungen möglichst einer dieser Kategorien zugeordnet werden:

- `[MARS-OFFICIAL]`
- `[GOOGLE-PLAY]`
- `[OPEN-SOURCE]`
- `[APK-OBSERVATION]`
- `[EXPERIMENTAL]`

Beispiel:

> `[APK-OBSERVATION]` In der untersuchten Legacy-App wurde der String `wind_set_speed` gefunden.

Das ist präziser als zu behaupten:

> „Der DF100M verwendet definitiv dieses Byteformat.“

---

## 7. Marken und Rechte

Mars Hydro, DF100M, Mars Legacy und weitere Produktnamen sind Marken bzw. Produktbezeichnungen der jeweiligen Rechteinhaber.

135er-Grow Central ist ein unabhängiges Community-/Reverse-Engineering-Projekt und steht nicht in Verbindung mit Mars Hydro.
