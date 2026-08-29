# GrowCentral Universal Raspberry Pi Image

This directory documents the reproducible 64-bit **universal image** for supported Raspberry Pi hardware.

<p align="center"><img src="brand/boot-splash-v0.9.png" alt="135er-Grow Central Raspberry Pi boot splash" width="760"></p>

## Hardware strategy

The image stays universal. Runtime model detection assigns one canonical support profile from `shared/hardware_profile.py`:

- Raspberry Pi 3B / 3B+ → `LEGACY_LITE`
- Raspberry Pi 4B / 400 / CM4 → `FULL_SUPPORT` standard
- Raspberry Pi 5 / CM5 → `FULL_SUPPORT` performance
- unknown hardware → `UNCLASSIFIED` conservative fallback

Pi 3 remains supported but must not constrain the feature baseline for Pi 4/5. Separate images are introduced only if different kernel/package/service bases become technically necessary.

## Base system

- Raspberry Pi OS Lite 64-bit / Debian 13 (Trixie)
- one image for Pi 3B/3B+, Pi 4/400, Pi 5 and compatible Compute Modules
- runtime model detection from device tree
- NetworkManager, systemd, BlueZ/BLE
- Python virtual environment with GrowCentral requirements
- diagnostics include detected model and support profile

## Resource profiles

### Legacy/Lite – Pi 3B/3B+

Conservative defaults: camera target up to 720p/reduced FPS, reduced kiosk effects, compact diagnostics history and conservative worker profile.

### Full Support – Pi 4/400/CM4

Full Nexus UI/Kiosk, standard worker profile, normal diagnostics history and full-support camera path.

### Full Support Performance – Pi 5/CM5

Full UI/Kiosk, performance worker profile and extended diagnostics history.

## First boot

1. Flash the universal image.
2. Join `135er-GrowCentral-Setup-XXXX`.
3. Open `http://10.42.0.1/`.
4. Complete network and credential setup.
5. After provisioning use `http://135er-GrowCentral.local/` or the assigned IP.
6. Verify the detected hardware profile in diagnostics.

The setup AP is restored automatically if the selected WLAN cannot be reached.

## Safe defaults

- `DF100M_ALLOW_WRITES=false`
- `GC_REMOTE_COMMANDS=false`
- `GC_CLOUD_ENABLED=false`
- root SSH login disabled
- UFW enabled
- unattended security updates enabled

## Automatic build

`.github/workflows/build-pi3-image.yml` produces the universal ARM64 image, verifies the base checksum, installs GrowCentral and dependencies, performs boot/reboot and consistency checks, compresses the result and publishes an Actions artifact plus prerelease assets.

The workflow name is historical; its output is the project-wide **universal image**, not a Pi-3-only image.

## Validation

CI must test the profile classifier for Pi 3, Pi 4/400, Pi 5 and CM4/CM5. Real validation is recorded separately per support class according to `docs/HARDWARE_TEST_PLAN.md`.

Policy: `docs/HARDWARE_SUPPORT_POLICY.md`.
