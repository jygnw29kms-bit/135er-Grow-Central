# 135er-Grow Central Universal Device Platform v1

## Ziel

Grow Central behandelt Hersteller nicht als Kernlogik. Der Core arbeitet ausschließlich mit normalisierten Geräteklassen und Capabilities. Hersteller-, Cloud-, BLE-, MQTT- und Gateway-Protokolle enden an einem Provider.

`Automation / UI / Grow Engine -> Entity & Capability Model -> Provider -> Transport -> Hardware`

Der Raspberry Pi bleibt die autoritative lokale Instanz. Cloud ist optional.

## First-Class Provider ab v1

- Mars Hydro
- Spider Farmer
- Tuya / Smart Life
- AC Infinity
- VIVOSUN
- Shelly
- Zigbee
- Grow Central ESP32
- TP-Link Tapo
- FRITZ! Smart Home
- Home Assistant Bridge
- Generic MQTT

Ein Provider im Katalog bedeutet nicht automatisch, dass jedes Modell des Herstellers validiert ist. Modell- und Firmware-Support wird getrennt geführt.

## Supportstufen

1. `detected` – Provider/Erkennung vorhanden, keine allgemeine Schreibfreigabe.
2. `experimental` – Protokoll oder Teilfunktionen implementiert, Hardwaretests laufen.
3. `compatible` – technische Integration für definierte Modelle nutzbar.
4. `validated` – echte Hardware und definierte Kernfunktionen wurden geprüft.
5. `certified` – definierte Modell-/Firmware-Kombination vollständig freigegeben.

## Device Classes

`light`, `fan`, `switch`, `pump`, `humidifier`, `dehumidifier`, `heater`, `sensor`, `camera`, `controller`, `gateway`.

## Capabilities

Der v1-Vertrag umfasst u. a. `power`, `brightness`, `fan_speed`, `oscillation`, `temperature`, `humidity`, `vpd`, `ppfd`, `soil_moisture`, `soil_temperature`, `ec`, `ph`, `voltage`, `current`, `power_meter`, `energy`, `schedule`, `mode`, `snapshot`, `stream`.

Automationen dürfen keine herstellerspezifischen Datenpunkte, UUIDs oder Topic-Namen verwenden.

## Transport

Provider können einen oder mehrere Transporte besitzen: BLE, Local Wi-Fi, Cloud, MQTT, Zigbee, USB, Serial, HTTP/RPC oder Bridge.

Local-first bedeutet: Ist ein validierter lokaler Transport verfügbar, wird er gegenüber Cloud bevorzugt. Cloud darf nicht zur Voraussetzung für lokale Regelung werden.

## Schreibsicherheit

- Keine generischen Rohbefehle für nicht validierte Modelle.
- Commands werden Capability-basiert validiert.
- Kritische Aktoren benötigen nach Möglichkeit State/ACK-Verifikation.
- Retries sind begrenzt und nachvollziehbar.
- Fail-safe ist geräteklassenabhängig: Bewässerung fällt sicher AUS; Abluft darf in einem sicheren Notmodus weiterlaufen; Licht folgt bei Kommunikationsverlust bevorzugt einem lokalen/geräteinternen Zeitplan.
- Jede Freigabe ist modell- und möglichst firmwarebezogen.

## Discovery

Die UI zeigt einen einzigen Vorgang „Geräte suchen“. Intern können Provider parallel BLE, LAN, mDNS, MQTT, Zigbee-Gateway und Herstellerdiscovery ausführen. Ergebnisse werden anschließend in dasselbe `DiscoveredDevice`-Modell normalisiert.

## Native ESP32-Geräte

`growcentral_esp32` ist Referenzprovider für eigene optionale Hardware. Zieltransporte: MQTT und Local Wi-Fi, BLE für Provisioning/Discovery. ESP32-Geräte verwenden dieselben Capabilities wie Fremdgeräte und benötigen keine Sonderlogik in Automation oder GUI.

## Migration bestehender Integrationen

Vorhandene FRITZ!, Tapo, Shelly und Home-Assistant-Adapter bleiben zunächst funktionsfähig. Sie werden schrittweise hinter die universelle Device API verschoben. Bestehende `/api/v1/smarthome/*` Endpoints bleiben während der Übergangsphase kompatibel.

Die bisherige lokale GUI bleibt über `/legacy` erreichbar, bis alle Detailfunktionen in die Plattform-GUI migriert sind.

## GUI-Prinzip

Alle Oberflächen nutzen dieselbe Informationsarchitektur:

1. Übersicht / Grow Environment
2. Grow
3. Geräte & Provider
4. Automation
5. Energie
6. Kamera
7. System

Herstellernamen werden primär bei Discovery, Geräteinformationen und Supportstatus gezeigt. Der tägliche Betrieb orientiert sich an Funktion und Growbox.
