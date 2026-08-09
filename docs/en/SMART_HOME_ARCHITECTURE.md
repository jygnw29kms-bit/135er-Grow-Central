# Smart-Home Architecture – v0.6

The Raspberry Pi remains the master. Smart-home ecosystems extend GrowControl but do not own local safety policy.

## Integration path

- **Shelly Gen2+**: direct local JSON-RPC adapter.
- **Tapo**: through Home Assistant.
- **FRITZ!SmartHome / FRITZ!DECT**: through Home Assistant.
- **Apple Home / Siri**: through Home Assistant HomeKit Bridge.
- **Matter**: future native bridge target.

Every device must be registered server-side and marked `approved`; state-changing access additionally requires `writable`, the global smart-home enable switch and local API-token authentication.

See `../SMART_HOME_ARCHITECTURE.md`, `../INTEGRATIONS.md` and `../SECURITY_AND_TRUST_MODEL.md`.
