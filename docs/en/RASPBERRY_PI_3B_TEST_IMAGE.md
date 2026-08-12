# Raspberry Pi 3B Test Image

This document describes the reproducible **135er-Grow Central** test image for Raspberry Pi 3B / 3B+.

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

The current repository is copied to `/opt/135er-grow-central`. Python dependencies are installed into `/opt/135er-grow-central/.venv`.

After web provisioning is complete, the local service starts automatically via `135er-grow-central.service` and exposes the web/API interface on port `8080`.

```text
http://<PI-IP>:8080
```

## Temporary test credentials

For the first hardware tests only:

```text
Hostname: 135er-grow-central
LAN address: http://135er-grow-central.local:8080
SSH username: GrowCentral
SSH password: grow-central-test
API/application token: test
Cloud token: test
```

The setup portal requires a new `GrowCentral` password of at least twelve characters before the main system can start.

## First-boot web provisioning

1. After the first boot, join `135er-GrowCentral-Setup-XXXX`. The four-character suffix comes from the Pi WLAN MAC address.
2. Use the temporary WLAN key `grow-central-test`.
3. Open `https://10.42.0.1` and accept the locally generated device certificate once.
4. Sign in with `GrowCentral` / `grow-central-test`. PAM verifies these credentials against the real system user.
5. Select target WLAN or LAN, hostname, timezone and a new `GrowCentral` password.
6. After a successful connection check, the setup access point stops and the main service starts.

If the target WLAN connection fails, the setup access point is restored automatically. Target WLAN passwords are stored only in NetworkManager's root-protected configuration and are never logged.

The setup network uses dual stack. Its reliable primary IPv4 path always uses
`10.42.0.1/24` on the Raspberry Pi, and NetworkManager assigns DHCP client
addresses from `10.42.0.10` through `10.42.0.250`. The portal starts only after
the DHCP listener is confirmed active. IPv6 is provided in parallel through shared mode. The complete AP
profile is reapplied on every start so an interrupted first boot repairs itself
automatically. The subsequently configured WLAN connection automatically uses
IPv4 and IPv6 whenever the target network provides both protocols.

## Security state in the test image

- root SSH login disabled
- password SSH enabled for the fixed headless user `GrowCentral`
- UFW enabled
- incoming TCP 22 and TCP 8080 allowed; during setup TCP 80/443 plus DHCP 67/UDP and DNS 53/TCP+UDP are additionally allowed only on the `wlan0` setup network
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

The image is built reproducibly with GitHub Actions. The official Raspberry Pi OS image is downloaded and verified against a pinned SHA256. The root filesystem is then expanded, Grow Central is installed, the image is compressed and a final SHA256 is generated.

Outputs:

```text
135er-Grow-Central_RPi3B_Test.img.xz
135er-Grow-Central_RPi3B_Test.img.xz.sha256
135er-Grow-Central_RPi3B_Test-CREDENTIALS.txt
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
2. Boot the Pi and complete the web provisioning process described above.
3. Find the new IP address in the portal/router.
4. Test SSH: `ssh GrowCentral@<PI-IP>`.
5. Open the web interface: `http://<PI-IP>:8080`.
7. Check the service: `systemctl status 135er-grow-central`.
8. Check Bluetooth: `bluetoothctl show`.
9. Fully close the Mars Legacy app before BLE tests.
10. Initially only discover/connect, inspect GATT/services and capture notifications. Enable writes only after protocol validation.
