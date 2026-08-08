# Raspberry Pi 3B Test Image

This document describes the reproducible **135er GrowControl** test image for Raspberry Pi 3B / 3B+.

## Base

- Raspberry Pi OS Lite 64-bit
- Debian 13 / Trixie
- Raspberry Pi 3B / 3B+
- systemd
- Python virtual environment
- Bluetooth / BlueZ
- SSH
- UFW
- unattended-upgrades

## Preinstalled project

The current repository is copied to `/opt/135er-growcontrol`. Python dependencies are installed into `/opt/135er-growcontrol/.venv`.

The local service starts automatically via `135er-growcontrol.service` and exposes the web/API interface on port `8080`.

```text
http://<PI-IP>:8080
```

## Temporary test credentials

For the first hardware tests only:

```text
Hostname: growcontrol-test
SSH username: test
SSH password: test
API/application token: test
Cloud token: test
```

These credentials are intentionally insecure and must be replaced after testing.

## Security state in the test image

- root SSH login disabled
- password SSH enabled for temporary user `test`
- UFW enabled
- incoming TCP 22 and TCP 8080 allowed
- automatic security updates enabled
- DF100M writes disabled by default
- remote cloud commands disabled by default
- cloud disabled by default

## DF100M test configuration

```text
DF100M_NAME_HINT=MZ_MZF002
DF100M_WRITE_UUID=f5d2b3fe-e6b5-49b5-aa5f-a00bb4156d1d
DF100M_NOTIFY_UUID=83677baa-3eb8-4866-b6b6-96e5ed5cc48d
DF100M_SPEED_MODE=byte
DF100M_ALLOW_WRITES=false
```

UUIDs and payload modes are reverse-engineering candidates and are not yet validated vendor protocol documentation.

## Image build

The image is built reproducibly with GitHub Actions. The official Raspberry Pi OS image is downloaded and verified against a pinned SHA256. The root filesystem is then expanded, GrowControl is installed, the image is compressed and a final SHA256 is generated.

Outputs:

```text
135er_GrowControl_RPi3B_Test.img.xz
135er_GrowControl_RPi3B_Test.img.xz.sha256
135er_GrowControl_RPi3B_Test-CREDENTIALS.txt
```

The finished image is intended to be published as both a GitHub Actions artifact and GitHub prerelease. Large binary disk images are intentionally not stored directly in normal Git history.

## Known build history

The first builder run failed because the downloaded base image was accidentally copied into the target root filesystem and exhausted available space.

The fix includes:

- excluding `base.img.xz`, `work.img` and build outputs from `rsync`
- enlarging the image before installation
- expanding the root partition and ext4 filesystem
- a separate v2 workflow for the corrected test build

## First hardware test

1. Flash the `.img.xz` to an SD card with Raspberry Pi Imager or a compatible tool.
2. Connect the Raspberry Pi 3B to the local network over Ethernet.
3. Boot the Pi.
4. Find its IP address in the router/DHCP server.
5. Test SSH: `ssh test@<PI-IP>`.
6. Open the web interface: `http://<PI-IP>:8080`.
7. Check the service: `systemctl status 135er-growcontrol`.
8. Check Bluetooth: `bluetoothctl show`.
9. Fully close the Mars Legacy app before BLE tests.
10. Initially only discover/connect, inspect GATT/services and capture notifications. Enable writes only after protocol validation.
