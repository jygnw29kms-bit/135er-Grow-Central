Grow-Central Soil Node

Hardware
- Seeed Studio XIAO ESP32-C3
- Capacitive Soil Moisture Sensor HW-390 V2.0.0
- VCC -> 3V3
- GND -> GND
- AOUT -> A0 / D0 / GPIO2

Measured engineering references on the first node
- AIR_RAW: 3767
- WATER_RAW: 1310

Firmware 0.4.0 (build verified; hardware validation pending)
- 12-bit ADC on A0/GPIO2
- 64-sample acquisition windows
- 12.5% trimmed mean for outlier suppression
- Median, min/max, span and standard deviation diagnostics
- Exponential moving average for stable UI values
- Provisional 0-100% engineering scale between air and water
- Signal quality classification and sensor-fault detection
- Persistent calibration and network configuration in ESP32 NVS
- Stable device id derived from the ESP32 MAC, e.g. gc-soil-17caec
- Native Grow-Central MQTT protocol gc-esp32-mqtt-v1
- Retained announce, state and availability topics
- MQTT Last Will retained as offline
- Diagnostics in the MQTT state meta object
- State publication every 10 s or after >=0.5 percentage-point change
- Automatic Wi-Fi and MQTT reconnect
- Serial machine-readable GC_SOIL telemetry at 115200 baud

Grow-Central topics
- growcentral/v1/devices/<id>/announce
- growcentral/v1/devices/<id>/state
- growcentral/v1/devices/<id>/availability

The normalized state exposes soil_moisture. Raw ADC values, quality, sigma,
calibration references, RSSI, uptime and firmware remain diagnostics under meta.

Serial commands
INFO
CAL AIR
CAL WATER
RESET CAL
NET INFO
NET WIFI <ssid>|<password>
NET MQTT <host>|<port>|<user>|<password>
NET CA <base64-DER-certificate>
NET NAME <display name>
NET CLEAR
REBOOT

Typical first network setup
1. Find the Raspberry Pi private-LAN address.
2. Configure Wi-Fi, for example:
   NET WIFI MyWifi|MyPassword
3. Configure the broker's TLS listener, certificate and individual device account
   first (see docs/de/SENSOR_PAIRING.md), then provision the node over USB:
   NET CA <base64-DER-CA-certificate>
   NET MQTT 192.168.178.50|8883|<device-id>|<individual-password>
4. Check:
   NET INFO
5. Grow-Central discovers the signed announcement. Compare the INFO fingerprint,
   then explicitly accept the sensor with its name and room in Grow-Central.

Security and architecture
- The native node remains local-first; Internet connectivity is not required.
- The default Pi image listener is loopback-only. Provision TLS/8883 with
  individual accounts and topic ACLs before connecting network sensors.
- Remote/cloud MQTT is not the default architecture.
- Credentials can be configured for an external broker through NET MQTT.

Important calibration note
The air/water scale verifies the electronics and provides a useful engineering
normalization. It is not final volumetric water content. Once the actual grow
substrate is available, calibrate plant/substrate profiles against real dry and
field-capacity points. The water reference should not be interpreted as 100%
substrate VWC.

Build
python -m platformio run

Upload
python -m platformio run -t upload

Monitor
python -m platformio device monitor -p COM5 -b 115200

Manual trust and identity (0.3.0)
- Discovery never grants access to room data or control.
- Native sensor messages use the gc-signed-v1 envelope with ECDSA P-256/SHA-256.
- First boot creates a key in gc-identity NVS; private material is never logged.
- INFO prints GC_ID fingerprint. Compare its final 16 hex characters in GC.
- The operator accepts/rejects and chooses a name plus room. A fresh signed
  challenge response is required before acceptance and every productive read.
- Rejected/revoked devices remain blocked across rediscovery and restart.
- NET CLEAR removes network settings, not the identity key or calibration.
- Full NVS erase creates a new key. Revoke/reject and explicitly reset identity
  in GC; the previous key is permanently retired before accepting a replacement.

TLS broker provisioning via local USB only
- Device-to-broker connections require TLS/8883, a real CA and individual login.
- Store the public CA certificate as base64 DER with NET CA <certificate>.
- NET MQTT <host>|8883|<device-id>|<individual-password>
- Configure certificates, password file and topic ACLs on the Pi first. Examples
  are under deploy/mqtt; see docs/de/SENSOR_PAIRING.md for the migration steps.
- Certificate validation remains enabled. Time sync is required for TLS.
- BLE transfer of Wi-Fi/MQTT credentials is NOT implemented and remains disabled.
- No network command accepts Wi-Fi passwords or actuator commands.

Autonomy
- ADC sampling runs in a separate measurement task, independent of TLS/MQTT I/O.
- Wi-Fi/MQTT retries back off independently up to 60 seconds.
- Identity proofs use a bounded queue and publish outside the MQTT callback,
  as required by the 256dpi MQTT library to avoid callback deadlocks.
- Flash/NVS encryption, secure boot, offline history backfill, BLE secure
  provisioning and physical long-duration tests remain separate work.
- No real sensor was flashed during the cloud validation.

Guided USB onboarding (0.4.0)
- USB ID <nonce> returns a signed announcement and the fresh challenge nonce.
- The current Pi test image bundles checked firmware and installs it through GC.
- GC provisions local CA/account credentials over USB and compares MQTT identity
  before the explicit name/room acceptance. See docs/de/USB_SENSOR_SETUP.md.
