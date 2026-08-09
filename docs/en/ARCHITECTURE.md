# Architecture

```text
Browser / iPad
      │
      ▼
Grow Central Local UI
      │
      ▼
FastAPI on Raspberry Pi
      │
      ├── BLE ──► DF100M
      ├── local data / future automation
      └── Cloud Link ──HTTPS──► Linux VPS
                                  ├── telemetry
                                  ├── history
                                  └── remote overview
```

## Local-first

Schedules, climate automation and device control should execute entirely locally.

## Cloud

The cloud must not become a single point of failure. It receives telemetry and provides remote data.

## Adapter principle

Device-specific protocol logic belongs in adapters. UI, automation and cloud consume normalized state.
