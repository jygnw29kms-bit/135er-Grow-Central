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

Firmware 0.2.0
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
NET NAME <display name>
NET CLEAR
REBOOT

Typical first network setup
1. Find the Raspberry Pi private-LAN address.
2. Configure Wi-Fi, for example:
   NET WIFI MyWifi|MyPassword
3. Configure the local Grow-Central broker. Empty user/password are allowed on
   the Pi image's LAN-only broker:
   NET MQTT 192.168.178.50|1883||
4. Check:
   NET INFO
5. Grow-Central discovers the retained announcement automatically through the
   existing growcentral_esp32 provider.

Security and architecture
- The native node remains local-first; Internet connectivity is not required.
- The Pi image MQTT listener is firewalled to RFC1918/private-LAN source ranges.
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
