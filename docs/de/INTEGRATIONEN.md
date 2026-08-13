# Integrationen – alpha-0.7.5

Grow Central bleibt **local-first**, unterstützt aber dort einen WAN-/Cloud-Pfad, wo der Hersteller diesen für Fernzugriff vorsieht. Lokale und entfernte Pfade werden getrennt behandelt und dürfen die Sicherheitsregeln des Raspberry Pi nicht umgehen.

## Mars Hydro

Verbindliche Projektbasis:

- **Mars Hydro FC3000, Modelljahr 2024, mit USB-Port und iConnect-Unterstützung**
- **Mars Hydro iFresh / DF100-Serie mit iConnect**

Beide gehören in der Zielarchitektur zu einer gemeinsamen **Mars-Hydro/iConnect-Gerätefamilie**. Der bestehende DF100M-/`MZ_MZF002`-BLE-Code bleibt als experimenteller Diagnose-, Reverse-Engineering- und Fallbackpfad erhalten. Schreibzugriffe bleiben standardmäßig deaktiviert, bis reale Hardwaretests einen reproduzierbaren und sicheren Kommunikationsweg bestätigt haben.

Ausführlich: [Mars Hydro / iConnect Hardwareprofil](../MARS_HYDRO_ICONNECT.md)

## FRITZ!Box / FRITZ!SmartHome

Grow Central verwendet für FRITZ!SmartHome einen **nativen lokalen AVM-AHA-Pfad**. Die FRITZ!Box ist dabei Gateway zu ihren angemeldeten Smart-Home-Geräten.

Zielablauf:

```text
Grow Central
  -> FRITZ!Box Login
  -> AVM AHA / lokale Smart-Home-Schnittstelle
  -> Geräteliste
  -> FRITZ! Steckdose
```

Unterstützte Baseline:

- Box/Smart-Home-Gerät lokal ansprechen
- Gerätename und AIN
- erreichbar / offline
- Schaltzustand
- Ein / Aus
- aktuelle Leistung in Watt
- Gesamtenergie in Wh/kWh

FRITZ!-Zugangsdaten dürfen ausschließlich serverseitig auf dem Raspberry Pi liegen und werden weder an die öffentliche Website noch an Browser-APIs ausgegeben.

## TP-Link Tapo

Tapo wird als **Hybrid-Integration** modelliert:

1. **Local path:** authentifizierte Gerätekommunikation im selben LAN/WLAN über `python-kasa`.
2. **WAN/Cloud path:** Fernzugriff über den TP-Link/Tapo-Account bleibt Teil der Zielarchitektur und darf für Remote-Betrieb erhalten bleiben.

Die GUI zeigt ein Tapo-Gerät nur einmal und soll den aktiven Verbindungsweg kennzeichnen, z. B. `LOCAL`, `CLOUD`, `LOCAL+CLOUD` oder `OFFLINE`.

Aktuelle Baseline:

- account-assisted lokale Discovery
- Authentifizierungsprüfung über echten Device-Update
- lokaler Adapter für Zustand und Schalten
- Leistung/Energie soweit vom Modell über die lokale Schnittstelle bereitgestellt
- WAN-Fähigkeit als Capability modelliert

Wichtig: Der aktuelle native Tapo-Adapter implementiert den **lokalen** Daten-/Steuerpfad. Ein vollwertiger TP-Link-Cloud-Transport wird nicht vorgetäuscht und bleibt separat zu implementieren und gegen reale Geräte zu validieren.

## Netzwerk- und Gerätesuche

Die lokale GUI muss bei jedem Scan sichtbar rückmelden:

- `SCAN LÄUFT`
- Trefferzahl
- `0 GERÄTE`
- Timeout
- Authentifizierungsfehler
- Backend-/Netzwerkfehler

FRITZ!Box, Tapo, Shelly und spätere Matter-Ziele werden als Provider getrennt erkannt. Nach erfolgreicher FRITZ!-Authentifizierung wird die hinter der Box liegende Smart-Home-Geräteliste abgefragt.

## Weitere Integrationen

- **Shelly Gen2+**: nativer lokaler JSON-RPC-Pfad.
- **Home Assistant**: optionaler Interoperabilitäts-Connector.
- **Apple Home/Siri**: Home Assistant HomeKit Bridge.
- **Logitech C920**: Linux-Kamerapfad mit `ffmpeg`, `v4l-utils` und Video-Gruppenzugriff im Image.
- **Matter**: späteres natives Ziel.

## Sicherheitsregeln

- Raspberry Pi bleibt lokale Master-Instanz.
- Zugangsdaten sind serverseitig und dürfen nicht in Logs erscheinen.
- Schreibzugriffe bleiben deny-by-default und benötigen Gerätefreigabe, writable-Flag, Authentifizierung und Audit.
- Cloud/WAN darf lokale Freigaben nicht umgehen.
- **ESP32 ist kein Bestandteil der Zielarchitektur.**
