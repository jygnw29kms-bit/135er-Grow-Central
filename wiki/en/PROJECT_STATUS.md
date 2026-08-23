# Project Status

**Version:** `alpha-0.7.5`  
**Master anchor:** `e339602`  
**Next Raspberry Pi hardware test:** **Build 118**  
**Tag:** `pi-universal-alpha-0.7.5-118`  
**Status:** `CANDIDATE` – not yet hardware-validated

Build 117 was successfully tested but is now superseded by the consolidated e339 master state.

## Currently integrated

- local-first FastAPI / GrowCentral GUI
- GrowCentral Nexus UI
- first boot, setup AP, LAN/WLAN and mDNS
- persistent device registry
- FRITZ! Smart Home
- local Tapo onboarding
- rooms, plants, grow journal and automation
- energy/cost baseline
- Logitech C920 / UVC, snapshot, MJPEG and V4L2
- firmware/model/USB-ID-aware camera LED capability detection
- guarded LED control when support is detected
- Elecrow 7-inch touch kiosk
- Nexus Mobile Android + iOS sideload clients
- Cloud Server V6
- signed APT repository at `https://repo.dezender.de/apt`

## Experimental / further validation required

- real FRITZ!/Tapo hardware paths where devices are available
- Mars Hydro iConnect
- DF100M BLE diagnostics/reverse engineering
- camera LED behavior on target camera/firmware
- Elecrow kiosk on target hardware

## Next milestone

Boot and test Build 118 on real hardware: first boot, networking, GUI, persistence, C920 including LED capabilities, and the relevant device/display paths. Only then may the candidate be promoted to `VALIDATED`.

Canonical references: [Release State](../../RELEASE_STATE.md) · [Build 118 Notes](../../docs/RELEASE_NOTES_BUILD_118.md) · [Release Pipeline](../../docs/RELEASE_PIPELINE.md)
