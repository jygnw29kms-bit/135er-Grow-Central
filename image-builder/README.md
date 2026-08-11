# Raspberry Pi 3B Test Image / Test-Image

This directory documents the reproducible Raspberry Pi 3B image build used for the first 135er-Grow Central hardware tests.

<p align="center"><img src="brand/boot-splash-v0.9.png" alt="135er-Grow Central Raspberry Pi boot splash" width="760"></p>

## Base system

- Raspberry Pi OS Lite 64-bit
- Debian 13 (Trixie)
- Raspberry Pi 3B / 3B+ compatible
- systemd
- BlueZ / Bluetooth LE
- Python virtual environment with the project requirements preinstalled

## Temporary test credentials

**These credentials are intentionally temporary and insecure.**

- Hostname: `grow-central-test`
- SSH user: `GrowCentral`
- SSH password: `grow-central-test`
- Locale/timezone: `de_DE.UTF-8`, `Europe/Berlin`
- Keyboard: German (`de`), variant `nodeadkeys`
- Interactive first-boot user setup: disabled
- Grow Central/API token: `test`
- Web UI: `http://<PI-IP>:8080`

The same temporary credentials protect the setup WLAN and authenticate the web portal. The portal requires a new password with at least 12 characters before completing setup.

## First-boot web setup / Web-Ersteinrichtung

1. Flash the image and start the Raspberry Pi.
2. Join `135er-GrowCentral-Setup-XXXX` with WLAN key `grow-central-test`.
3. Open `https://10.42.0.1` and accept the local device certificate once.
4. Sign in as `GrowCentral` with password `grow-central-test`.
5. Select WLAN or LAN, set hostname/timezone and choose a new GrowCentral password.
6. After a successful connection test, the setup AP stops and the main service starts.

DE: Schlägt die Verbindung zum gewählten WLAN fehl, wird der Setup-Zugangspunkt automatisch wieder aktiviert. EN: If the selected WLAN cannot be reached, the setup access point is restored automatically.

## Safe defaults

- `DF100M_ALLOW_WRITES=false`
- `GC_REMOTE_COMMANDS=false`
- `GC_CLOUD_ENABLED=false`
- root SSH login disabled
- UFW enabled; TCP 80/443 is temporarily limited to the setup subnet, while TCP 22 and 8080 remain available for the appliance
- unattended security updates enabled

## Automatic build

`.github/workflows/build-pi3-image.yml` runs natively on a GitHub-hosted ARM64 runner. It downloads the official Raspberry Pi OS Lite image, verifies its SHA256 checksum, installs 135er-Grow Central and dependencies, enables SSH/Bluetooth/Grow Central services, installs the current full-screen Plymouth splash and console identity, compresses the resulting image and publishes it as both a GitHub Actions artifact and a prerelease asset.

## Current image branding

- Plymouth splash: `brand/boot-splash-v0.9.png`
- Interactive console banner: `brand/console-banner.txt`
- Combined identity: symbol + `135er-Grow Central` + `J.L.` signet
- Palette: Near Black, Neon Lime and Data Cyan

The generated file is named:

`135er-Grow-Central_RPi3B_Test.img.xz`

Flash it with Raspberry Pi Imager, balenaEtcher or another raw image writer. No private target WLAN credentials are embedded in the public test image.
