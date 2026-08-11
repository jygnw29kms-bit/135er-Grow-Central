# Raspberry Pi 3B Test Image

A reproducible Raspberry Pi 3B/3B+ test image based on Raspberry Pi OS Lite 64-bit / Debian 13 is used for the first hardware tests.

## Preinstalled

- 135er-Grow Central in `/opt/135er-grow-central`
- Python venv and project dependencies
- Bluetooth / BlueZ
- SSH
- UFW
- unattended-upgrades
- first-boot web provisioning through a temporary WLAN access point
- systemd start via `135er-grow-central.service` after provisioning succeeds

Web interface:

```text
http://<PI-IP>:8080
```

## Temporary credentials

```text
Hostname: grow-central-test
Username: GrowCentral
Password: grow-central-test
API/application token: test
Cloud token: test
```

**First boot only.** The portal requires a new password of at least twelve characters before the main service starts.

## First boot

1. Join `135er-GrowCentral-Setup-XXXX` with WLAN key `grow-central-test`.
2. Open `https://10.42.0.1` and accept the local certificate.
3. Sign in as `GrowCentral` with `grow-central-test`.
4. Configure target WLAN or LAN, hostname, timezone and a new password.
5. After validation, setup mode stops and Grow Central starts.

If the WLAN connection fails, the setup access point is restored automatically.

## Safe test defaults

- DF100M writes: disabled
- remote cloud commands: disabled
- cloud: disabled
- root SSH: disabled
- firewall: SSH (22/TCP), Grow Central (8080/TCP), plus temporary HTTP/HTTPS (80/443) from the setup subnet only

## Build and publication

GitHub Actions downloads the official Raspberry Pi OS image, verifies the pinned SHA256, expands the root partition/filesystem, installs Grow Central and creates:

```text
135er-Grow-Central_RPi3B_Test.img.xz
135er-Grow-Central_RPi3B_Test.img.xz.sha256
135er-Grow-Central_RPi3B_Test-CREDENTIALS.txt
```

The image is published as an Actions artifact/prerelease rather than committed as a large binary to normal Git history.

## Build correction

The first builder run exhausted the target root filesystem because the downloaded base image was accidentally copied into it. The corrected v2 builder excludes build files and expands the image, root partition and ext4 filesystem before installation.

## Test sequence

1. Flash the image to an SD card.
2. Complete first-boot web provisioning.
3. Determine its IP address.
4. Test `ssh GrowCentral@<PI-IP>`.
5. Open `http://<PI-IP>:8080`.
6. Check `systemctl status 135er-grow-central`.
7. Check `bluetoothctl show`.
8. Close the Mars Legacy app.
9. Discover/connect to DF100M, inspect GATT and capture notifications.
10. Do not perform BLE writes until the protocol is sufficiently validated.

Detailed technical documentation: `docs/en/RASPBERRY_PI_3B_TEST_IMAGE.md`.
