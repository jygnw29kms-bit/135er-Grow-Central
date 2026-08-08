# Raspberry Pi 3B Test Image

A reproducible Raspberry Pi 3B/3B+ test image based on Raspberry Pi OS Lite 64-bit / Debian 13 is used for the first hardware tests.

## Preinstalled

- 135er GrowControl in `/opt/135er-growcontrol`
- Python venv and project dependencies
- Bluetooth / BlueZ
- SSH
- UFW
- unattended-upgrades
- systemd autostart via `135er-growcontrol.service`

Web interface:

```text
http://<PI-IP>:8080
```

## Temporary credentials

```text
Hostname: growcontrol-test
Username: test
Password: test
API/application token: test
Cloud token: test
```

**Testing only.** Replace these credentials after the hardware tests.

## Safe test defaults

- DF100M writes: disabled
- remote cloud commands: disabled
- cloud: disabled
- root SSH: disabled
- firewall: only SSH (22/TCP) and GrowControl (8080/TCP)

## Build and publication

GitHub Actions downloads the official Raspberry Pi OS image, verifies the pinned SHA256, expands the root partition/filesystem, installs GrowControl and creates:

```text
135er_GrowControl_RPi3B_Test.img.xz
135er_GrowControl_RPi3B_Test.img.xz.sha256
135er_GrowControl_RPi3B_Test-CREDENTIALS.txt
```

The image is published as an Actions artifact/prerelease rather than committed as a large binary to normal Git history.

## Build correction

The first builder run exhausted the target root filesystem because the downloaded base image was accidentally copied into it. The corrected v2 builder excludes build files and expands the image, root partition and ext4 filesystem before installation.

## Test sequence

1. Flash the image to an SD card.
2. Connect the Pi over Ethernet and boot.
3. Determine its IP address.
4. Test `ssh test@<PI-IP>`.
5. Open `http://<PI-IP>:8080`.
6. Check `systemctl status 135er-growcontrol`.
7. Check `bluetoothctl show`.
8. Close the Mars Legacy app.
9. Discover/connect to DF100M, inspect GATT and capture notifications.
10. Do not perform BLE writes until the protocol is sufficiently validated.

Detailed technical documentation: `docs/en/RASPBERRY_PI_3B_TEST_IMAGE.md`.
