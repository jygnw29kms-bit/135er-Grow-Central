# Integrations – alpha-0.7.1

## Support levels

- **Implemented baseline** – code exists but still needs hardware validation.
- **Bridge path** – supported through a maintained interoperability layer.
- **Experimental** – reverse-engineered behavior not yet validated.
- **Planned** – architecture target only.

| Technology | Strategy | Status |
|---|---|---|
| DF100M | BLE | Experimental |
| Shelly Gen2+ | local JSON-RPC | Implemented baseline |
| Home Assistant | REST connector | Implemented baseline |
| Tapo | Home Assistant TP-Link integration | Bridge path |
| FRITZ!SmartHome | Home Assistant FRITZ!SmartHome integration | Bridge path |
| Apple Home/Siri | Home Assistant HomeKit Bridge | Bridge path |
| MQTT | scoped local bus | Planned |
| Matter | native bridge | Planned |

## Home Assistant connector restrictions

The current connector intentionally supports only registered `switch.*` entities and only `turn_on` / `turn_off`. It cannot proxy arbitrary service names, URLs or payloads.

## Shelly restrictions

The native adapter accepts a literal private/link-local IP address from the server-side device inventory. Browser requests never provide a target URL.

## Credentials

Credentials are referenced through environment-variable names in server-side configuration. They are never returned by the public device API.
