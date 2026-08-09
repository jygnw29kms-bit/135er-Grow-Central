# 135er GrowControl

**Secure local-first automation platform for Raspberry Pi, BLE devices and smart-home interoperability.**

> Current architecture generation: **v0.6 Secure Smart-Home Platform**

135er GrowControl began as a Raspberry-Pi controller for the Mars Hydro DF100M and is now being rebuilt as a modular local-first automation platform. The Raspberry Pi remains the authoritative controller; cloud services and smart-home ecosystems are optional integrations.

## Core principles

- Raspberry Pi is the local master.
- Local operation continues without internet access.
- No direct public exposure of the Pi control API by default.
- Device writes are deny-by-default, authenticated, validated and auditable.
- Vendor protocols are isolated behind adapters.
- Stable documented local APIs are preferred.
- Home Assistant is the optional interoperability bridge for Apple Home/Siri, FRITZ!SmartHome, Tapo and other ecosystems.
- Shelly Gen2+ gets a native local JSON-RPC adapter baseline.
- Matter is the long-term standards-based bridge target, not a rushed compatibility hack.
- Experimental DF100M reverse engineering remains clearly separated from validated support.

## Architecture

```text
Apple Home / Siri      FRITZ! / Tapo / other ecosystems
        \                         /
         \                       /
          +---- Home Assistant --+   optional bridge
                    |
                    | REST
                    v
           135er GrowControl Local
              Raspberry Pi
              /    |      \
             /     |       \
        BLE DF100M |        Shelly Gen2+ RPC
                    |
                 SQLite
                    |
             outbound HTTPS
                    v
              optional cloud
```

## Integration policy

| Integration | Strategy | Current status |
|---|---|---|
| Mars Hydro DF100M | BLE / controlled reverse engineering | Experimental hardware validation |
| Shelly Gen2+ | Direct local JSON-RPC | Adapter baseline implemented |
| Home Assistant | Local REST connector | Adapter baseline implemented |
| TP-Link Tapo | Via Home Assistant | Supported architecture path |
| FRITZ!SmartHome / FRITZ!DECT | Via Home Assistant | Supported architecture path |
| Apple Home / Siri | Home Assistant HomeKit Bridge | Supported architecture path |
| Generic MQTT | Local event/device bus | Planned baseline |
| Matter | Native bridge target | Planned |

## Security defaults

```text
DF100M_ALLOW_WRITES=false
GC_REMOTE_COMMANDS=false
GC_CLOUD_ENABLED=false
GC_SMARTHOME_ENABLED=false
GC_HA_READ_ONLY=true
GC_LOCAL_API_TOKEN=
```

If `GC_LOCAL_API_TOKEN` is not configured, protected write endpoints refuse control requests.

## Repository map

- `app/` – local FastAPI runtime
- `app/smarthome/` – normalized smart-home registry, policy and adapters
- `web/` – local Raspberry-Pi HUD
- `website/` – public static project website / GitHub Pages source
- `cloud/` – optional cloud alpha
- `database/` – local/cloud schema baselines
- `config/` – safe example device inventory
- `docs/` – canonical technical documentation
- `wiki/` – versioned wiki source
- `image-builder/` + workflows – Raspberry Pi image pipeline

## Documentation

- [`PROJECT_HISTORY.md`](PROJECT_HISTORY.md) – project history
- [`docs/PROJECT_STATUS.md`](docs/PROJECT_STATUS.md) – authoritative implementation status
- [`docs/ARCHITECTURE_MASTER.md`](docs/ARCHITECTURE_MASTER.md) – system architecture
- [`docs/SMART_HOME_ARCHITECTURE.md`](docs/SMART_HOME_ARCHITECTURE.md) – smart-home architecture
- [`docs/INTEGRATIONS.md`](docs/INTEGRATIONS.md) – integration strategy
- [`docs/SECURITY_AND_TRUST_MODEL.md`](docs/SECURITY_AND_TRUST_MODEL.md) – security boundaries
- [`docs/SMART_HOME_SOURCES.md`](docs/SMART_HOME_SOURCES.md) – official source references
- [`docs/HARDWARE_TEST_PLAN.md`](docs/HARDWARE_TEST_PLAN.md) – DF100M validation
- [`docs/DECISION_LOG.md`](docs/DECISION_LOG.md) – architecture decisions
- [`website/README.md`](website/README.md) – GitHub Pages/public website

## Important status rule

Documentation contains both implemented runtime and future architecture. A capability is only considered complete when `docs/PROJECT_STATUS.md` marks it as implemented/validated.
