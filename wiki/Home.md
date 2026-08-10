# 135er-Grow Central Wiki

## alpha-0.7.1 Secure Smart-Home Platform

135er-Grow Central is a local-first Raspberry-Pi automation platform. It started with DF100M BLE research and now includes a secured smart-home architecture for plugs, devices and ecosystem bridges.

```text
Apple Home / Siri      Tapo / FRITZ! / other ecosystems
        \                         /
         +---- Home Assistant ---+   optional
                    |
                    v
            135er-Grow Central
              Raspberry Pi
             /            \
        BLE DF100M       Shelly RPC
```

## Smart-home strategy

- Shelly Gen2+: native local JSON-RPC
- Tapo: Home Assistant bridge
- FRITZ!SmartHome: Home Assistant bridge
- Apple Home / Siri: Home Assistant HomeKit Bridge
- Matter: future native bridge target
- DF100M: BLE validation in progress

## Security

Discovery never grants write access. Devices must be registered and approved. State changes require per-device writable permission, global Smart-Home enablement and local write authentication.

## Documentation

- [Project status](../docs/PROJECT_STATUS.md)
- [Smart-home architecture](../docs/SMART_HOME_ARCHITECTURE.md)
- [Integrations](../docs/INTEGRATIONS.md)
- [Security model](../docs/SECURITY_AND_TRUST_MODEL.md)
- [Source register](../docs/SMART_HOME_SOURCES.md)
- [DF100M research](../docs/DF100M_RESEARCH_LOG.md)
- [Hardware tests](../docs/HARDWARE_TEST_PLAN.md)
- [Decision log](../docs/DECISION_LOG.md)
