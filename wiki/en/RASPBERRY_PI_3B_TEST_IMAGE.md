# Raspberry Pi Test Image · Build 118

**Version:** `alpha-0.7.5`  
**Master anchor:** `e339602`  
**Candidate:** **Build 118**  
**Tag:** `pi-universal-alpha-0.7.5-118`  
**Status:** `CANDIDATE` – not yet hardware-validated

Build 117 was successfully tested but is superseded by the consolidated e339 state. Build 118 is the next real hardware-test candidate.

## Image baseline

`.github/workflows/build-pi3-image.yml` builds the universal Raspberry Pi image on Raspberry Pi OS Lite 64-bit / Debian 13 (trixie). The GitHub Actions run number is written into the image as BUILD metadata.

## Included in the candidate

- Grow Central under `/opt/135er-grow-central`;
- first boot / setup AP / NetworkManager / mDNS;
- Bluetooth / BlueZ;
- local GrowCentral Nexus GUI;
- FRITZ! Smart Home and Tapo paths;
- Logitech C920/UVC, snapshot, MJPEG and dynamic V4L2 controls;
- firmware/model/USB-ID-aware camera LED capability detection;
- guarded LED control only when support is detected;
- Elecrow 7-inch touch kiosk with systemd service;
- support and diagnostics paths;
- SSH, firewall/hardening and update baseline.

## Access

```text
First boot: http://10.42.0.1/
After setup: http://135er-Grow-Central.local/
Compatibility: http://135er-Grow-Central.local:8080/
```

Temporary image credentials are test-only and must be replaced during first boot.

## Safe defaults

```text
DF100M_ALLOW_WRITES=false
GC_REMOTE_COMMANDS=false
GC_CLOUD_ENABLED=false
```

Unverified Mars Hydro/BLE write paths remain deny-by-default.

## Build 118 test sequence

1. flash exactly Build 118;
2. verify fresh boot;
3. verify setup AP / DHCP / DNS;
4. verify LAN/WLAN and mDNS;
5. complete first boot and open the GUI;
6. reboot;
7. verify persistence;
8. test C920 discovery, snapshot, MJPEG and V4L2;
9. test camera LED capability detection;
10. change LED state only if the target camera/firmware reports support;
11. test Elecrow kiosk if connected;
12. test FRITZ!/Tapo paths when hardware is available;
13. test Mars Hydro/BLE diagnostics without unverified writes;
14. generate `Grow-Central-Support-latest.tar.gz` for any unexpected deviation.

## Release rule

Build 118 remains `CANDIDATE` until the real hardware test passes. Documentation, website and Mobile-only changes do not justify an artificial Build 119; a new Pi build is needed only for an actual runtime fix/change.

Canonical: [Release State](../../RELEASE_STATE.md) · [Build 118 Notes](../../docs/RELEASE_NOTES_BUILD_118.md) · [Release Pipeline](../../docs/RELEASE_PIPELINE.md)
