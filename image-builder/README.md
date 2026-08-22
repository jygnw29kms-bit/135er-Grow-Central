# Universal Raspberry Pi 3+ Test Image / Test-Image

This directory documents the reproducible 64-bit image for Raspberry Pi 3B/3B+, 4B/400, 5 and compatible Compute Modules.

<p align="center"><img src="brand/boot-splash-v0.9.png" alt="135er-Grow Central Raspberry Pi boot splash" width="760"></p>

## Base system

- Raspberry Pi OS Lite 64-bit
- Debian 13 (Trixie)
- Raspberry Pi 3B / 3B+, 4B, 400 and 5 compatible
- Compute Module 3+/4/5 compatible when the carrier provides supported LAN/WLAN hardware
- runtime model detection from the device tree; `wlan0` is preferred with a NetworkManager Wi-Fi fallback
- systemd
- BlueZ / Bluetooth LE
- Python virtual environment with the project requirements preinstalled

## Temporary test credentials

**These credentials are intentionally temporary and insecure.**

- Hostname/domain: `135er-grow-central` / `135er-Grow-Central.local`
- SSH user: `GrowCentral`
- SSH password: `grow-central-test`
- Locale/timezone: `de_DE.UTF-8`, `Europe/Berlin`
- Keyboard: German (`de`), variant `nodeadkeys`
- Interactive first-boot user setup: disabled
- Grow Central/API token: `test`
- First and permanent Web UI: `http://10.42.0.1/` / `http://135er-Grow-Central.local/` (`:8080` remains compatible)

The same temporary credentials protect the setup WLAN and authenticate the normal main GUI. Setup is embedded in its System section and requires new system and GUI passwords with at least 12 characters.

## First-boot web setup / Web-Ersteinrichtung

1. Flash the image and start the Raspberry Pi.
2. Join `135er-GrowCentral-Setup-XXXX` with WLAN key `grow-central-test`.
3. Open `http://10.42.0.1/`.
4. Sign in as `GrowCentral` with password `grow-central-test`.
5. Open **System**, select LAN or WLAN, keep the fixed hostname and choose new system/GUI passwords. Enter the SSID manually if the Pi 3B cannot scan while its AP is active.
6. After network, DNS, GUI and mDNS readiness checks, the setup AP stops. Runtime health is retried for up to 60 seconds before failure recovery begins.

DE: Schlägt die Verbindung zum gewählten WLAN fehl, wird der Setup-Zugangspunkt automatisch wieder aktiviert. EN: If the selected WLAN cannot be reached, the setup access point is restored automatically.

## Support bundle

Persistent, size-limited journals survive reboots. First boot and systemd failures automatically create `/var/lib/135er-grow-central/support/Grow-Central-Support-latest.tar.gz`; the authenticated GUI can generate and download a new bundle under **System**. Always attach this redacted archive to a problem report.

## Safe defaults

- `DF100M_ALLOW_WRITES=false`
- `GC_REMOTE_COMMANDS=false`
- `GC_CLOUD_ENABLED=false`
- root SSH login disabled
- UFW enabled; TCP 80 is the simple authenticated GUI entry point, TCP 8080 remains compatible, TCP 22 provides SSH, and setup DHCP/DNS rules stay limited to the setup interface
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
