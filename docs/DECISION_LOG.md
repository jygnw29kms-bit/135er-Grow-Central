# Architecture Decision Log

## ADR-001 – Raspberry Pi is the master
All local safety-critical control remains authoritative on the Pi.

## ADR-002 – No ESP32 core architecture
One Raspberry-Pi deployment model remains the project standard.

## ADR-003 – Optional cloud is outbound-only
The Pi is not directly published to the internet.

## ADR-004 – SQLite local / PostgreSQL cloud target
Low local operational complexity; scalable relational cloud model.

## ADR-005 – Vendor protocols live behind adapters
UI and automations target normalized capabilities, not vendor payloads.

## ADR-006 – Home Assistant is the interoperability bridge
Apple Home/Siri, Tapo, FRITZ!SmartHome and broad ecosystem compatibility are handled through a maintained optional bridge instead of duplicating every vendor protocol.

## ADR-007 – Shelly Gen2+ gets a native local adapter
Shelly documents a local JSON-RPC interface suitable for direct local control.

## ADR-008 – Tapo direct protocol is not v0.6 core
Tapo is supported through Home Assistant to reduce credential duplication and protocol churn risk.

## ADR-009 – FRITZ!SmartHome uses the Home Assistant bridge in v0.6
This avoids adding another credential/authentication implementation to the GrowControl core while still supporting FRITZ smart plugs and related devices.

## ADR-010 – Apple Home uses HomeKit Bridge first
Practical local Apple Home/Siri interoperability is achieved through Home Assistant. Native Matter bridging remains the standards-based future target.

## ADR-011 – Discovery never grants write permission
Every controllable device requires explicit inventory approval and a writable flag.

## ADR-012 – No arbitrary proxy APIs
Browser/cloud callers cannot choose arbitrary LAN URLs, vendor methods or Home Assistant service names.

## ADR-013 – Protected writes fail closed without a local token
An unset token disables protected write endpoints rather than silently allowing them.
