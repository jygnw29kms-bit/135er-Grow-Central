# Mars Hydro / iConnect Hardware Profile

**Project:** 135er-Grow Central  
**Phase:** alpha-0.7.4  
**Status:** architecture and hardware-profile baseline; direct control paths still require target-hardware validation.

## Authoritative project hardware

### Mars Hydro FC3000

The project target is the **Mars Hydro FC3000, model year 2024**, explicitly the generation with:

- USB port
- iConnect support
- integration target: shared Mars Hydro/iConnect device family

Older FC3000 generations without this interface set are not the reference hardware for implementation or documentation.

### Mars Hydro iFresh / DF100 family

Within this project, **DF100** refers to the **Mars Hydro iFresh series** using iConnect. It must not be modeled as an unrelated standalone fan family.

### DF100M / observed BLE identity

Historical development work observed a device advertising as or related to:

```text
MZ_MZF002
Firmware observed: V1.8
```

The repository contains BLE discovery, GATT inspection, notification capture, and guarded experimental write tooling for this path.

This BLE path is now classified as:

- diagnostics
- reverse engineering
- fallback / compatibility research

It is **not** the architectural primary integration path for the Mars Hydro ecosystem.

## Target abstraction

```text
FC3000 2024 ───────────────┐
                           │
iFresh / DF100 ────────────┼──► MarsHydro/iConnect abstraction
                           │
DF100M BLE diagnostics ────┘
```

The abstraction should expose normalized capabilities such as:

- device identity
- online/offline state
- light power / dim level where supported
- fan power / speed where supported
- mode / schedule where supported
- temperature/humidity data only when actually provided by the connected hardware path
- diagnostics and last-contact state

No capability is considered implemented merely because it exists conceptually in the common model.

## Safety and trust rules

1. The Raspberry Pi remains the local authority.
2. No ESP32 is part of the target architecture.
3. Direct device writes are deny-by-default.
4. Unknown or reverse-engineered writes remain disabled until replayed and validated on real hardware.
5. iConnect-related cloud or account credentials must never be exposed to the public website or browser-side code.
6. The optional project cloud is not allowed to bypass local approval, writable flags, authentication, or audit.
7. If a local iConnect-compatible path cannot be validated, the software must expose the limitation rather than silently switching to unsafe guessed commands.

## Validation matrix

| Function | FC3000 2024 | iFresh / DF100 | DF100M BLE diagnostics |
|---|---|---|---|
| identity | required | required | observed baseline |
| discovery | pending validation | pending validation | baseline exists |
| read status | pending validation | pending validation | experimental |
| control | pending validation | pending validation | disabled by default |
| scheduling | pending validation | pending validation | not validated |
| error recovery | pending validation | pending validation | partial diagnostics only |

## Current conclusion

The project now treats **Mars Hydro FC3000 2024** and **Mars Hydro iFresh / DF100** as one iConnect-oriented ecosystem. Existing DF100M BLE code remains useful, but only as an experimental diagnostic/fallback path until the actual local iConnect communication path is proven and documented.
