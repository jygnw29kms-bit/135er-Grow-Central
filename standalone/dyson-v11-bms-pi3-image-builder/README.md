# Dyson V11 BMS Pi3 Image Builder

Standalone Raspberry Pi 3 image builder for the local **135er Dyson Service
Center**. Version 0.3.0 fixes the former CAN-only detection path: the documented
Dyson V11 data protocol is monitored passively over UART (115200/8N1), while
SocketCAN remains available as an optional adapter/legacy monitor.

## Scope
- Raspberry Pi 3 / armhf
- Raspberry Pi OS Bookworm Lite base via `pi-gen`
- Passive Dyson UART/TLV monitor with frame size, marker, CRC8 and CRC32 checks
- Automatic discovery of `/dev/serial/by-id`, `ttyACM`, `ttyUSB` and Pi UART devices
- Automatic rotation across multiple UART adapters instead of sticking to the first enumerated port
- Layered diagnostic page: OS → adapter → port → raw signal → Dyson protocol
- Detection of serial-console conflicts, permission errors and disappearing adapters
- SWD programmer/OpenOCD availability checks (without automatically touching the target)
- SocketCAN support with link, bus-state and error-counter diagnostics
- Local web GUI on port `8080`
- Downloadable JSON diagnostic report and timestamped event log
- Explicit read-only battery probe (Battery Type + Status) for a battery connected without a vacuum
- UART and CAN interface setup
- systemd autostart

> Safety: all automatic monitoring is passive. Only the technician-triggered
> probe transmits, and it contains Battery-Type/Status read TLVs only. The
> service does not send control/write TLVs, connect to an SWD target, flash
> firmware, disable, reset, spoof, bypass or rewrite protection parameters.

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
- UART: automatic device selection, default 115200 baud
- CAN (optional): `can0`, default 500000 bit/s

Open **Diagnose** in the GUI. A V11 battery is reported as detected only after
a genuine battery response (not a request echo) has passed the role, size,
`0xC0` marker, CRC8 and CRC32 checks. For a standalone battery, use **Akku
sicher abfragen**. The probe scans all discovered UART ports and sends two
read-only requests per port. The exported report shows the precise failing
layer and a concrete repair hint.

## Diagnostic API

- `GET /api/diagnostics` – complete current diagnostic snapshot
- `POST /api/diagnostics/run` – create a new timestamped snapshot
- `POST /api/serial/probe` – run the bounded Battery-Type/Status read probe
- `GET /api/diagnostics/export` – download JSON report including recent events
- `GET /api/serial/frames` – recent validated/invalid UART frames
- `POST /api/serial` – select serial device and baud rate
- `GET /api/frames` – optional SocketCAN frame buffer

This directory is standalone and has no runtime dependency on Grow-Central.

## Package install / update

```bash
curl -fsSL https://dezender.de/dyson-v11-bms/install.sh | sudo bash
```

Existing 0.2/0.3 installations must run the checksum-verified migration once
to install the current repository key and APT source:

```bash
curl -fsSL https://dezender.de/dyson-v11-bms/update.sh | sudo bash
```

All later releases are delivered through the normal operating-system update:

```bash
sudo apt update
sudo apt upgrade
```
