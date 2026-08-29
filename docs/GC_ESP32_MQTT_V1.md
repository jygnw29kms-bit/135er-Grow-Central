# Grow Central ESP32 MQTT Protocol v1

## Purpose

`gc-esp32-mqtt-v1` is the native reference protocol for Grow Central sensor and actuator modules. It is local-first and broker-based. Cloud access is optional and must not be required for local control.

## Topic root

Default root: `growcentral/v1`

Per device (`<id>` must be stable and lowercase):

- `growcentral/v1/devices/<id>/announce` — retained device manifest
- `growcentral/v1/devices/<id>/state` — retained normalized state
- `growcentral/v1/devices/<id>/set` — commands from Grow Central
- `growcentral/v1/devices/<id>/ack` — command acknowledgement
- `growcentral/v1/devices/<id>/availability` — retained `online` / `offline` (LWT)

## Announce payload

```json
{
  "schema": "gc-device-v1",
  "protocol": "gc-esp32-mqtt-v1",
  "id": "soil-01",
  "name": "Substrat Sensor 1",
  "device_class": "sensor",
  "model": "GC-SOIL-ESP32",
  "firmware": "0.1.0",
  "capabilities": ["soil_moisture", "soil_temperature", "ec"]
}
```

The announce message is retained. A device must republish it when firmware or capability declarations change.

## State payload

```json
{
  "ts": "2026-08-29T20:00:00Z",
  "soil_moisture": 48.2,
  "soil_temperature": 23.7,
  "ec": 1.42
}
```

State keys MUST use `gc-device-v1` capability names. Vendor- or firmware-specific raw keys are not permitted in the normalized state object; diagnostics may be placed under `meta`.

## Command payload

```json
{
  "command_id": "2f52f4c4b1a14501b8aef2cb01e08ba3",
  "capability": "power",
  "value": true
}
```

An actuator MUST reject undeclared capabilities and invalid values.

## ACK payload

```json
{
  "command_id": "2f52f4c4b1a14501b8aef2cb01e08ba3",
  "ok": true,
  "state": {"power": true}
}
```

Failed commands use `ok:false` and a short `error` string. Grow Central treats a command without a matching ACK as unconfirmed and must not silently assume success.

## Availability and fail-safe

Every module SHOULD configure MQTT Last Will on its availability topic with retained payload `offline`, then publish retained `online` after connecting.

Safety-critical actuators MUST define their local fallback behavior in firmware. Network loss must never by itself start irrigation or another potentially damaging actuator.

## Broker assumptions

Grow Central uses a local MQTT broker or a configured LAN broker. TLS and credentials are supported for remote brokers, but an Internet-hosted broker is not the default architecture.
