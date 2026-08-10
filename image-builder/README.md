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
- SSH user: `test`
- SSH password: `test`
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

`.github/workflows/build-pi3-image-v2.yml` downloads the official Raspberry Pi OS Lite image, verifies its SHA256 checksum, installs 135er-Grow Central and dependencies, enables SSH/Bluetooth/Grow Central services, installs the current full-screen Plymouth splash and console identity, and performs an automated ARM64 QEMU boot smoke test. The image and a Windows QEMU boot kit are published as GitHub Actions artifacts and prerelease assets.

## Current image branding

- Plymouth splash: `brand/boot-splash-v0.9.png`
- Interactive console banner: `brand/console-banner.txt`
- Combined identity: symbol + `135er-Grow Central` + `J.L.` signet
- Palette: Near Black, Neon Lime and Data Cyan

The generated file is named:

`135er-Grow-Central_RPi3B_Test.img.xz`

Flash it with Raspberry Pi Imager, balenaEtcher or another raw image writer. Ethernet is recommended for the first test because no WLAN SSID/password is embedded in the public test image.

## QEMU test on Windows

Download both the image and `135er_Grow_Central_RPi3B_Test-QEMU-Windows-Kit.zip` from the same release. Extract the kit, place the `.img.xz` beside its scripts and run `start-qemu-windows.cmd`. The script extracts the image and starts the included kernel/initramfs with QEMU ARM64.

- Web UI: `http://localhost:8080`
- SSH: `ssh -p 2222 test@localhost`
- Login: `test / test`

This validates ARM64 boot, systemd, networking, SSH and the web application without a Raspberry Pi. Bluetooth, GPIO, Raspberry Pi firmware and physical DF100M communication still require real hardware.
