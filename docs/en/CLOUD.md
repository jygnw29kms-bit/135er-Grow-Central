# GrowControl Cloud

The cloud optionally runs on a Linux VPS.

## Responsibilities

- receive telemetry
- store history
- expose latest site state
- provide a remote dashboard
- prepared command queue

## Security

Remote commands require two opt-ins:

1. `CLOUD_ALLOW_COMMANDS=true` on the server
2. `GC_REMOTE_COMMANDS=true` on the Pi

The Pi validates commands again locally.
