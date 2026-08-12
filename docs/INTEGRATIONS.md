# Integrations – alpha-0.7.4

## Support levels

- **Implemented baseline** – code exists but still needs hardware validation.
- **Bridge path** – supported through a maintained interoperability layer.
- **Experimental** – reverse-engineered behavior not yet validated.
- **Planned / validation pending** – architecture target exists but the real device path is not yet proven.

| Technology / device | Strategy | Status |
|---|---|---|
| Mars Hydro FC3000 (2024, USB, iConnect) | shared Mars Hydro/iConnect abstraction | Planned / validation pending |
| Mars Hydro iFresh / DF100 | shared Mars Hydro/iConnect abstraction | Planned / validation pending |
| DF100M / MZ_MZF002 BLE | diagnostics / reverse engineering / fallback | Experimental |
| Shelly Gen2+ | local JSON-RPC | Implemented baseline |
| Home Assistant | REST connector | Implemented baseline |
| Tapo | local/cloud discovery work + Home Assistant bridge path | Bridge path / validation pending |
| FRITZ!SmartHome | Home Assistant / AVM integration path | Bridge path |
| Apple Home/Siri | Home Assistant HomeKit Bridge | Bridge path |
| Logitech C920 | local Linux video stack (`ffmpeg`, `v4l-utils`) | Image baseline / hardware validation pending |
| MQTT | not part of the current core architecture | Deferred |
| Matter | native bridge | Planned |

## Mars Hydro rule

The authoritative project hardware is the **Mars Hydro FC3000 model year 2024 with USB port and iConnect support** plus the **Mars Hydro iFresh/DF100 family using iConnect**. These devices are modeled as one vendor ecosystem. Existing DF100M BLE code remains an experimental diagnostics/fallback path and must not be presented as the primary architectural integration.

See [MARS_HYDRO_ICONNECT.md](MARS_HYDRO_ICONNECT.md).

## Raspberry Pi authority

The Raspberry Pi remains the local master for device policy, web UI, automation, diagnostics, audit, and optional cloud communication. **ESP32 is explicitly excluded from the target architecture.**

## Home Assistant connector restrictions

The current connector intentionally supports only registered `switch.*` entities and only `turn_on` / `turn_off`. It cannot proxy arbitrary service names, URLs or payloads.

## Shelly restrictions

The native adapter accepts a literal private/link-local IP address from the server-side device inventory. Browser requests never provide a target URL.

## Credentials

Credentials are referenced through environment-variable names in server-side configuration. They are never returned by the public device API. iConnect-related account or cloud credentials, if later required, must follow the same server-side-only rule.
