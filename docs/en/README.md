# 135er GrowControl – English

135er GrowControl is a **local-first control and monitoring platform** for Raspberry Pi with an optional cloud layer on a Linux VPS.

## Goals

- local device communication without permanent vendor-app dependency
- central web interface
- DF100M BLE research and later control
- local automation even without Internet
- optional cloud for remote overview and history
- modular adapters for additional devices

## Core principles

1. The Raspberry Pi remains the master.
2. The cloud is optional.
3. Remote commands are validated again locally.
4. Experimental BLE writes are disabled by default.
5. Device protocols are separated from the UI.
6. Sources and assumptions are clearly labeled.

## v0.4.1 status

- BLE discovery: implemented
- connect / disconnect: implemented
- GATT inspection: implemented
- notifications: experimental
- speed payload: not validated
- cloud telemetry: alpha
- cloud history: alpha
- remote commands: prepared, disabled by default
- FC3000: planned
- sensors / VPD: planned
