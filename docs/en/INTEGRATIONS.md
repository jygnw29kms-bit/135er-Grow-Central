# Integrations – alpha-0.7.4

Grow Central uses direct vendor protocols only where a stable, reviewable local path exists.

## Mars Hydro

Authoritative project hardware:

- **Mars Hydro FC3000, model year 2024, with USB port and iConnect support**
- **Mars Hydro iFresh / DF100 series using iConnect**

Both are modeled as one shared **Mars Hydro/iConnect device family**. The earlier representation of DF100/DF100M as only a standalone BLE device is no longer the primary architecture.

Existing DF100M / `MZ_MZF002` BLE code remains as an experimental diagnostics, reverse-engineering, and fallback path. Writes stay disabled by default until real-hardware tests confirm a reproducible and safe communication path.

See [Mars Hydro / iConnect hardware profile](../MARS_HYDRO_ICONNECT.md).

## Other integrations

- **Shelly Gen2+**: native local JSON-RPC path.
- **TP-Link Tapo**: discovery/import work and Home Assistant bridge path; login and real-device search still require hardware validation.
- **FRITZ!SmartHome**: Home Assistant / AVM path.
- **Apple Home/Siri**: Home Assistant HomeKit Bridge.
- **Logitech C920**: Linux camera path with `ffmpeg`, `v4l-utils`, and video-group access included in the image baseline.
- **Matter**: later native target.

The Home Assistant connector is intentionally not an arbitrary service proxy: the current baseline allows only registered `switch.*` entities and on/off commands.

The Raspberry Pi remains the local master. **ESP32 is explicitly not part of the target architecture.**
