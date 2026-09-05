# Dyson V11 BMS Pi3 Image Builder

Standalone Raspberry Pi 3 image builder for a local Dyson V11 BMS/CAN diagnostics appliance.

## Scope
- Raspberry Pi 3 / armhf
- Raspberry Pi OS Bookworm Lite base via `pi-gen`
- SocketCAN support
- Local web GUI on port `8080`
- CAN interface/bitrate setup
- Read-only CAN frame monitor and health view
- systemd autostart

> Safety: this project does not include commands that disable, reset, spoof, bypass, or rewrite battery protection parameters.

## Build
```bash
sudo apt-get update
sudo apt-get install -y git coreutils quilt parted qemu-user-static debootstrap zerofree zip dosfstools bsdtar libarchive-tools pigz xz-utils
./build.sh
```

The compressed image is copied into `deploy/`.

## First boot
- Hostname: `dyson-v11-bms`
- GUI: `http://<pi-ip>:8080`
- Service: `dyson-bms-ui.service`
- CAN: `can0`, default 500000 bit/s

This directory is standalone and has no runtime dependency on Grow-Central.
