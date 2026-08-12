# Integrationen – alpha-0.7.4

Grow Central verwendet direkte Herstellerprotokolle nur dort, wo ein stabiler und nachvollziehbarer lokaler Weg vorhanden ist.

## Mars Hydro

Verbindliche Projektbasis:

- **Mars Hydro FC3000, Modelljahr 2024, mit USB-Port und iConnect-Unterstützung**
- **Mars Hydro iFresh / DF100-Serie mit iConnect**

Beide gehören in der Zielarchitektur zu einer gemeinsamen **Mars-Hydro/iConnect-Gerätefamilie**. Die frühere Darstellung von DF100/DF100M als ausschließlich eigenständigem BLE-Gerät gilt nicht mehr als Primärarchitektur.

Der bestehende DF100M-/`MZ_MZF002`-BLE-Code bleibt als experimenteller Diagnose-, Reverse-Engineering- und Fallbackpfad erhalten. Schreibzugriffe bleiben standardmäßig deaktiviert, bis reale Hardwaretests einen reproduzierbaren und sicheren Kommunikationsweg bestätigt haben.

Ausführlich: [Mars Hydro / iConnect Hardwareprofil](../MARS_HYDRO_ICONNECT.md)

## Weitere Integrationen

- **Shelly Gen2+**: nativer lokaler JSON-RPC-Pfad.
- **TP-Link Tapo**: Erkennung/Import und Home-Assistant-Bridge; Login- und reale Gerätesuche bleiben hardwareseitig zu prüfen.
- **FRITZ!SmartHome**: Home-Assistant-/AVM-Pfad.
- **Apple Home/Siri**: Home Assistant HomeKit Bridge.
- **Logitech C920**: Linux-Kamerapfad mit `ffmpeg`, `v4l-utils` und Video-Gruppenzugriff im Image.
- **Matter**: späteres natives Ziel.

Der Home-Assistant-Connector ist absichtlich kein beliebiger Service-Proxy: Nur registrierte `switch.*`-Entities und Ein/Aus-Befehle sind im aktuellen Baselinepfad zugelassen.

Der Raspberry Pi bleibt die lokale Master-Instanz. **ESP32 ist kein Bestandteil der Zielarchitektur.**
