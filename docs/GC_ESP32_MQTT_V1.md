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

## Grow-Central Soil Node reference implementation

The repository reference node lives in `firmware/gc-soil-node` and currently targets the Seeed Studio XIAO ESP32-C3 with a HW-390 V2 capacitive probe.

The node derives a stable lowercase device id from its ESP32 hardware identity and publishes only the normalized `soil_moisture` capability in the state body. Sensor diagnostics are carried under `meta`, including raw/filtered ADC values, median, min/max, standard deviation, quality class, calibration references, Wi-Fi RSSI, uptime and firmware version.

Network onboarding is intentionally local. Initial Wi-Fi and broker settings can be written over USB serial and are persisted in ESP32 NVS:

```text
NET WIFI <ssid>|<password>
NET CA <base64-DER-of-broker-CA>
NET MQTT <broker-host>|8883|<device-id>|<individual-password>
NET INFO
```

The Pi image keeps its development listener on 127.0.0.1:1883 only. Native nodes use an explicitly configured TLS listener on TCP/8883 with individual credentials and topic ACLs. The first-boot firewall permits 8883 only from RFC1918/private-LAN ranges. The TLS listener is not created before its real certificates and password file exist. Internet/cloud MQTT is not required for native nodes.

After MQTT connection the node publishes retained `online`, retained `announce`, and retained `state`. An unexpected disconnect therefore changes retained availability to `offline` through MQTT Last Will. Grow Central's `growcentral_esp32` provider discovers the retained announcement and exposes the node through the standard device platform. Native ESP32 nodes can also be assigned to Grow Central rooms; their normalized soil-moisture values are included in room sensor history and the room UI.

For capacitive probes, the engineering air/water endpoints are not a universal agronomic calibration. Grow Central should keep per-substrate calibration/profile data because dielectric response varies with substrate composition, salinity/EC and temperature.


## Mandatory manual trust layer (firmware 0.3.0)

The examples above describe the application payloads, not authorization. Native
announcements and measurements use the `gc-signed-v1` envelope documented in
[Sensor pairing](en/SENSOR_PAIRING.md). Legacy unsigned announcements may appear
as DISCOVERED for migration, but they cannot be accepted or contribute room data.

Four persistent states apply: DISCOVERED, TRUSTED, REJECTED and REVOKED. The user
must select a name and room and compare the physical key fingerprint. Fresh,
non-retained nonce proofs authenticate acceptance, live state reads and health.
Rejected/revoked devices do not reappear as new candidates. Availability text
alone is advisory and is never used as identity or live-state evidence.

The native pairing policy grants read-only access. It does not authorize actuator
commands, even if an announcement claims an actuator capability. Operator
configuration of separate validated actuator policies is outside this step.

Wi-Fi/MQTT credential transfer over BLE is unavailable and disabled. Local USB
configuration remains the supported path; do not send credentials through MQTT.
