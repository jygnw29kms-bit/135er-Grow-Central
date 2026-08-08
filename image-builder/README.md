# Raspberry Pi 3B Test Image / Test-Image

This directory documents the reproducible Raspberry Pi 3B image build used for the first 135er GrowControl hardware tests.

## Base system

- Raspberry Pi OS Lite 64-bit
- Debian 13 (Trixie)
- Raspberry Pi 3B / 3B+ compatible
- systemd
- BlueZ / Bluetooth LE
- Python virtual environment with the project requirements preinstalled

## Temporary test credentials

**These credentials are intentionally temporary and insecure.**

- Hostname: `growcontrol-test`
- SSH user: `test`
- SSH password: `test`
- GrowControl/API token: `test`
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

`.github/workflows/build-pi3-image.yml` downloads the official Raspberry Pi OS Lite image, verifies its SHA256 checksum, installs 135er GrowControl and dependencies, enables SSH/Bluetooth/GrowControl services, compresses the resulting image and publishes it as both a GitHub Actions artifact and a prerelease asset.

The generated file is named:

`135er_GrowControl_RPi3B_Test.img.xz`

Flash it with Raspberry Pi Imager, balenaEtcher or another raw image writer. Ethernet is recommended for the first test because no WLAN SSID/password is embedded in the public test image.
