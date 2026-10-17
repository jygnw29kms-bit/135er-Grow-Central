# Grow-Central Integrations-Support-Matrix

Stand: 2026-10-17

Ziel: bestätigte Hersteller-/Standardfunktionen werden übernommen, sofern sie für Grow-Central funktionell relevant sind. Vermutete oder nur reverse-engineerte Schreibfunktionen bleiben gesperrt, bis sie auf realer Hardware validiert wurden.

## Statusklassen

- `gc_hardware_validated`: auf eigener Grow-Central-Hardware bzw. mit realem Zielgerät getestet.
- `vendor_verified`: Herstellerdokumentation, offizielles Protokoll oder etablierte Upstream-Integration bestätigt die Funktion.
- `community_verified_readonly`: belastbar dokumentiert/reverse-engineert, in Grow-Central zunächst nur lesend.
- `candidate`: technisch plausibel, aber noch nicht ausreichend verifiziert.

## Integrationen

| Integration | Bestätigte/relevante Funktionen | GC-Status | Schreibzugriff |
|---|---|---|---|
| MQTT | QoS, retained messages, Last Will, Keepalive, TLS-fähiger Transport, Publish/Subscribe | vendor_verified | erlaubt nur über explizites GC-Schema + ACK/Policy |
| Grow-Central ESP32 MQTT | signierte Device-ID, announce/state/availability, TLS, LWT, Challenge/Proof | gc_hardware_validated für bestehenden Soil-Node-Pfad | nur definierte sichere Befehle |
| Home Assistant MQTT | MQTT Discovery, eindeutige IDs, Availability, Birth/LWT | vendor_verified | opt-in/allowlist |
| Home Assistant Bridge | Snapshot-Export, Messwerte, freigegebene Switches | gc_hardware_validated im Softwarepfad | nur allowlisted Geräte |
| FRITZ!SmartHome | AHA HTTP, AIN-Geräteidentität, Schalten/Status, Steckdosenmesswerte je Capability | vendor_verified | nur freigegebene Geräte |
| FRITZ!Box Tools | TR-064-basierte Router-/Netzwerkfunktionen, Polling | vendor_verified | nur explizit benötigte Funktionen |
| TP-Link Tapo | WLAN-Geräte, lokale Bedienung je Modell; P110/P115 Energieüberwachung; Tapo Open API für Partner/Cloud | vendor_verified | modell-/adapterabhängig, keine unbestätigten Befehle |
| Shelly | lokaler Smart-Home-Adapter bleibt bevorzugter Weg für vorhandene Geräte | gc_hardware_validated soweit bestehender Adapter/Teststand reicht | Policy + allowlist |
| Spider Farmer GGS | BLE-Gerätesuche, GGS-App nutzt Bluetooth und 2,4-GHz-WLAN; bekannte Telemetriestruktur im GC-Provider | vendor_verified für BT/WLAN-Grundfunktion, community_verified_readonly für GC-Telemetriepfad | gesperrt bis reale Modell/Firmware-Validierung |
| Mars Hydro / MarsPro | vorhandener GC-Provider für Cloud-MQTT-Telemetrie, Sensor-/Controllerwerte normalisierbar | community_verified_readonly | gesperrt bis reale Modell/Firmware-Validierung |
| Zigbee2MQTT | MQTT-basierte Geräte-/Sensorintegration über bestehende Bridge | vendor_verified/upstream | über deklarierte Capabilities |
| Tuya Local | bestehender lokaler Integrationspfad | candidate/adapterabhängig | nur explizit freigegebene Geräte |

## Funktionsprinzip

Grow-Central implementiert bestätigte Funktionen möglichst über bestehende, gepflegte Protokolle/Bibliotheken und dünne Adapter. Keine zweite Parallelimplementierung, wenn bereits ein geprüfter Transportadapter existiert.

Jede Integration liefert normalisierte Capabilities wie:

`power`, `brightness`, `fan_speed`, `temperature`, `humidity`, `vpd`, `ppfd`, `soil_moisture`, `soil_temperature`, `ec`, `ph`, `voltage`, `current`, `energy`.

## Sicherheitsregeln

1. Lesen darf breiter unterstützt werden als Schreiben.
2. Schreibzugriff wird nur aktiviert, wenn Modell/Firmware und Semantik validiert sind.
3. Cloud-Zwang wird vermieden, wenn ein stabiler lokaler Weg existiert.
4. Zugangsdaten liegen im Credential Store bzw. root-lesbaren Konfigurationspfaden, nicht im Frontend oder Repo.
5. Geräte müssen explizit freigegeben sein; Discovery bedeutet nicht automatisch Trust.
6. Fremde Payloads werden auf bekannte Felder/Capabilities begrenzt.
7. MQTT-Schreibbefehle verwenden eindeutige Command-IDs und ACKs.

## Verifizierte Quellen, die wir funktionell nutzen

- MQTT 5.0: QoS, retained messages, Last Will, Keepalive und TLS-fähige Transportschicht.
- Home Assistant: MQTT Discovery, Availability sowie Birth/Last-Will-Verhalten.
- FRITZ!: AHA HTTP für Smart-Home-Aktoren; TR-064 für FRITZ!Box-Funktionen.
- Tapo: modellabhängige lokale Bedienbarkeit; P110/P115 mit Energieüberwachung; offizielle Open-API existiert für Partnerintegration.
- Spider Farmer GGS: Herstellerhandbuch bestätigt Bluetooth-Erkennung und 2,4-GHz-WLAN-Einrichtung des Controllers.

## Build-Regel

Neue bestätigte Capability darf in den nächsten Build aufgenommen werden, wenn:

- Quelle/Protokoll nachvollziehbar dokumentiert ist,
- Lizenz und Abhängigkeit geprüft sind,
- Eingaben normalisiert und validiert werden,
- kein gefährlicher Schreibpfad ohne reale Hardwarevalidierung entsteht,
- Tests für Parser/Normalisierung/Policy vorhanden sind.

So übernehmen wir Bekanntes, ohne aus einem Grow-Controller eine Sammlung hoffnungsvoller Protokollgerüchte zu machen.
