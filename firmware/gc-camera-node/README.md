# 135er-GC-Cam – Grow Central ESP32-CAM node

Target: AI Thinker style ESP32-CAM with OV2640 and microSD.

Identity and discovery:
- Display name: `135er-GC-Cam`
- LAN/DHCP/mDNS hostname: `135er-gc-cam` (`135er-gc-cam.local`)
- Native GC device id: `gc-cam-<MAC suffix>`
- Grow Central protocol: `gc-esp32-mqtt-v1`
- Device class: `camera`
- Capabilities: `snapshot`, `stream`
- Signed ECDSA P-256 announcement and challenge proof; private key remains in NVS.
- New devices remain `DISCOVERED` until manually accepted and assigned to a room in Grow Central.

Provisioning:
- An unconfigured camera starts the existing encrypted Grow Central BLE provisioning flow.
- The camera sensor is deliberately not started during first-time BLE provisioning because AI Thinker GPIO0 is both camera XCLK and the physical provisioning confirmation pin.
- After encrypted credentials are saved the node reboots, starts the camera, joins Wi-Fi and announces itself to GC.
- `NET CLEAR` over the local serial console removes network credentials and returns to BLE provisioning.

Network services:
- `http://135er-gc-cam.local/health` is a non-sensitive health endpoint.
- Snapshot and MJPEG stream URLs are reported only inside signed GC state/proof payloads and contain a random 128-bit local camera token.
- `POST /capture?token=...` stores a JPEG on the SD card.
- mDNS advertises `_http._tcp` with service metadata but never advertises Wi-Fi, MQTT credentials or the camera access token.

SD storage:
- The camera expects one FAT32 data partition of at least 2 GiB.
- It creates `/gc/snapshots`, `/gc/timelapse`, `/gc/logs`, `/gc/recovery` and `/gc/device.json`.
- Wi-Fi passwords, MQTT passwords, CA material, private identity key and camera token are never written to the SD card.
- A legacy Raspberry-Pi `bootfs` partition is intentionally rejected as too small instead of being silently used.

Serial diagnostics (115200 baud):
- `INFO`
- `USB ID <64-hex nonce>`
- `NET CLEAR`
- `REBOOT`

Build:
```text
cd firmware/gc-camera-node
pio run
```

Flash the firmware into the ESP32 itself. The microSD is data storage; it is not the ESP32 firmware boot medium.
