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
- SSH password: `test`
- Locale/timezone: `de_DE.UTF-8`, `Europe/Berlin`
- Keyboard: German (`de`), variant `nodeadkeys`
- Interactive first-boot user setup: disabled
- Grow Central/API token: `test`
- Web UI: `http://<PI-IP>:8080`

Change all test credentials after the initial hardware test.

## Safe defaults

- `DF100M_ALLOW_WRITES=false`
- `GC_REMOTE_COMMANDS=false`
- `GC_CLOUD_ENABLED=false`
- root SSH login disabled
- UFW enabled; only TCP 22 and 8080 allowed inbound
- unattended security updates enabled

## Automatic build

`.github/workflows/build-pi3-image-v2.yml` downloads the official Raspberry Pi OS Lite image, verifies its SHA256 checksum, installs 135er-Grow Central and dependencies, enables SSH/Bluetooth/Grow Central services, installs the current full-screen Plymouth splash and console identity, compresses the resulting image and publishes it as both a GitHub Actions artifact and a prerelease asset.

## Current image branding

- Plymouth splash: `brand/boot-splash-v0.9.png`
- Interactive console banner: `brand/console-banner.txt`
- Combined identity: symbol + `135er-Grow Central` + `J.L.` signet
- Palette: Near Black, Neon Lime and Data Cyan

The generated file is named:

`135er-Grow-Central_RPi3B_Test.img.xz`

Flash it with Raspberry Pi Imager, balenaEtcher or another raw image writer. Ethernet is recommended for the first test because no WLAN SSID/password is embedded in the public test image.

## QEMU test on Windows

QEMU uses a separate Debian 13 ARM64 image because the Raspberry Pi kernel is designed for Pi hardware and does not provide the complete virtual device path required for a reliable Windows test. `.github/workflows/build-qemu-arm64-image.yml` installs the same Grow Central application into a VirtIO-capable image, boots it in QEMU and verifies `/api/health` before publishing `135er_Grow_Central_QEMU_ARM64-Windows.zip`.

- Web UI: `http://localhost:8080`
- SSH: `ssh -p 2222 test@localhost`
- Login: `test / test`

Run `start-qemu-arm64-windows.cmd` from the extracted package. This validates ARM64 boot, systemd, networking, SSH and the web application without a Raspberry Pi. Bluetooth, GPIO, Raspberry Pi firmware and physical DF100M communication still require real hardware.
