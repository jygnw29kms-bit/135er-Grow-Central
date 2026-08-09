# Project History

135er GrowControl started as a practical Raspberry Pi solution for a Mars Hydro DF100M because the existing setup worked with the Mars Legacy app while the newer Mars Hydro app was not usable reliably.

The project evolved from a fan-control prototype into a local-first platform: BLE discovery and protocol research, FastAPI/Bleak runtime, responsive dark HUD design, optional outbound-only VPS cloud, local SQLite and cloud PostgreSQL direction, RBAC/data-domain modeling, schedules/automation concepts, audit/backup targets and finally a reproducible Raspberry Pi 3B test-image pipeline.

Core decisions include: Raspberry Pi remains the master, no ESP32 dependency, cloud is optional, Pi port 8080 is not exposed publicly, remote commands require local validation, and DF100M writes remain disabled until hardware validation.

Target device:

```text
Identifier: MZ_MZF002_0_A0A3B35EFDC8
Device ID: A0A3B35EFDC8
Firmware: V1.8
```

The immediate milestone is real-device GATT/notification capture and controlled Legacy-app correlation before any write protocol is marked validated.
