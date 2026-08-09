# Smart-Home-Architektur – v0.6

Der Raspberry Pi bleibt Master. Smart-Home-Systeme erweitern GrowControl, übernehmen aber nicht die lokale Sicherheitslogik.

## Integrationsweg

- **Shelly Gen2+**: direkter lokaler JSON-RPC-Adapter.
- **Tapo**: über Home Assistant.
- **FRITZ!SmartHome / FRITZ!DECT**: über Home Assistant.
- **Apple Home / Siri**: über Home Assistant HomeKit Bridge.
- **Matter**: späteres natives Bridge-Ziel.

Jedes Gerät muss serverseitig registriert, `approved` und für Schreibzugriffe zusätzlich `writable` sein. Zusätzlich müssen Smart-Home-Schreibzugriffe global aktiviert und mit einem lokalen API-Token authentifiziert werden.

Siehe auch `../SMART_HOME_ARCHITECTURE.md`, `../INTEGRATIONS.md` und `../SECURITY_AND_TRUST_MODEL.md`.
