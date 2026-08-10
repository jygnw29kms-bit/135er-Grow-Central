# 135er-Grow Central · Documentation (English)

[Deutsch](../de/README.md) · [Documentation hub](../README.md) · [Repository](../../README.md)

135er-Grow Central is a **local-first control and monitoring platform** for Raspberry Pi with an optional cloud layer on a Linux VPS.

## Goals

- local device communication without permanent vendor-app dependency
- central responsive web interface
- DF100M BLE research and later control
- local automation even without Internet
- optional cloud for remote overview and history
- modular adapters for additional devices
- reproducible Raspberry Pi test images for hardware testing

## Core principles

1. The Raspberry Pi remains the master.
2. The cloud is optional.
3. Remote commands are validated again locally.
4. Experimental BLE writes are disabled by default.
5. Device protocols are separated from the UI.
6. Sources and assumptions are clearly labeled.
7. Large system images are published as release/Actions artifacts rather than stored in normal Git history.

## alpha-0.7.1 · Hardware validation status

- BLE discovery: implemented
- connect / disconnect: implemented
- GATT inspection: implemented
- notifications: experimental
- DF100M speed payload: not validated
- cloud telemetry / history: alpha
- remote commands: prepared, disabled by default
- full-platform data model and RBAC: defined
- Debian/Ubuntu/Raspberry Pi installer baseline: available
- GUI target and responsive rules: defined
- Raspberry Pi 3B/3B+ image builder: available
- preinstalled Pi test image: build/test phase
- FC3000: planned
- sensors / VPD: platform prepared

## Current test documentation

- [Raspberry Pi 3B Test Image](RASPBERRY_PI_3B_TEST_IMAGE.md)
- [GUI Target](GUI_PREVIEW.md)
- [DF100M Protocol Research](DF100M_PROTOCOL.md)
- [Cloud](CLOUD.md)
- [Installation](INSTALLATION.md)

The test image temporarily uses `test` / `test` and token `test`. These credentials are intended only for the first local hardware tests and must be replaced afterwards.
