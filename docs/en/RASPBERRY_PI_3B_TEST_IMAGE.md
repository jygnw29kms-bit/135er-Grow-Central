# Universal Raspberry Pi Image with Hardware Profiles

> This filename is historical. The current GrowCentral image is **not Pi-3-only**; it is the project-wide universal image.

## Supported hardware

- Raspberry Pi 3B / 3B+ → **Legacy/Lite**
- Raspberry Pi 4B / 400 / Compute Module 4 → **Full Support Standard**
- Raspberry Pi 5 / Compute Module 5 → **Full Support Performance**

Pi 3 remains supported with conservative resource limits. New Full-Support features are designed against Pi 4/5 rather than being constrained by Pi 3 performance.

## Canonical runtime detection

The model is read from `/proc/device-tree/model`. `shared/hardware_profile.py` is the single source of truth for classification and is consumed by diagnostics and hardware-aware runtime paths.

Legacy/Lite uses conservative defaults including camera up to 1280×720, reduced frame-rate targets, reduced kiosk effects, compact diagnostics history and conservative workers. Pi 4/5 Full-Support profiles may use camera modes up to 1920×1080.

## Image strategy

GrowCentral keeps **one universal image**. Separate images are introduced only when different kernel, package or service bases become technically necessary.

## Base system

- Raspberry Pi OS Lite 64-bit / Debian 13 Trixie
- NetworkManager, systemd, Bluetooth/BlueZ, SSH, UFW
- GrowCentral runtime in `/opt/135er-grow-central`
- first boot through setup AP and captive portal
- local GUI at `http://135er-GrowCentral.local/`
- diagnostics expose detected model and support profile

## First boot

1. Flash the universal image.
2. Join `135er-GrowCentral-Setup-XXXX`.
3. Open `http://10.42.0.1/`.
4. Configure network and separate GUI/system-SSH credentials.
5. Finish setup and reboot.
6. Open `http://135er-GrowCentral.local/` or the assigned IP.
7. Verify the detected hardware model and profile in diagnostics.

The setup AP is automatically restored if the selected WLAN cannot be reached.

## Security baseline

- root SSH disabled
- UFW enabled
- unattended security updates
- DF100M writes disabled by default
- remote cloud commands disabled by default
- cloud disabled by default

## Validation

Real hardware validation is tracked separately for Legacy/Lite Pi 3, Full-Support Pi 4/400, and Full-Support Performance Pi 5. A Pi-3-specific Legacy/Lite regression does not automatically block a Pi-4/5 Full-Support release, but must be documented transparently.

See [`../HARDWARE_TEST_PLAN.md`](../HARDWARE_TEST_PLAN.md) and [`../HARDWARE_SUPPORT_POLICY.md`](../HARDWARE_SUPPORT_POLICY.md).
