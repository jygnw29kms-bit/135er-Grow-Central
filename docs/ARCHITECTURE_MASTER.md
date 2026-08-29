# Architecture Master – 135er-Grow Central

## 1. Architectural goal

GrowCentral is a local-first control platform in which loss of internet, cloud or vendor services does not remove local observability and automation. The Raspberry Pi is the authoritative local master.

## 2. Hardware architecture

GrowCentral uses **one universal Raspberry Pi image** with one central runtime hardware classifier.

```text
Universal Image
     |
/proc/device-tree/model
     |
shared/hardware_profile.py
     |
     +-- LEGACY_LITE -------- Pi 3B / 3B+
     +-- FULL_SUPPORT ------- Pi 4 / 400 / CM4
     +-- FULL_SUPPORT PERF -- Pi 5 / CM5
     +-- UNCLASSIFIED ------- conservative fallback
```

This classifier is an architectural boundary. Runtime components must consume it instead of inventing independent model checks.

### Support policy

- Pi 3B/3B+ remains supported as Legacy/Lite.
- Pi 4/400/5 define the Full-Support feature baseline.
- Pi 3 performance limits must not constrain future Full-Support functionality.
- Separate images are permitted only when different kernel/package/service bases become technically necessary.

## 3. Logical topology

```text
Browser / Tablet / Mobile
          |
          v
135er-Grow Central Local
   Universal Raspberry Pi
          |
   Hardware Profile
   /   |    |    \
Devices Camera Kiosk Diagnostics
          |
     Local Automation
          |
 optional outbound HTTPS
          |
       Cloud V7
```

## 4. Runtime resource profiles

### Legacy/Lite – Pi 3B / 3B+

Conservative workers, compact diagnostics history, reduced kiosk effects and conservative camera limits (currently up to 1280×720 / reduced FPS target).

### Full Support Standard – Pi 4 / 400 / CM4

Full Nexus UI/Kiosk, standard workers, normal diagnostics history and Full-Support camera modes up to 1920×1080 when advertised by the camera.

### Full Support Performance – Pi 5 / CM5

Full UI/Kiosk, performance workers, extended diagnostics history and the Full-Support camera path.

## 5. Device authority and adapters

Device-specific protocol logic remains isolated from GUI/business logic. Known capabilities, authentication, writable flags and audit remain mandatory. No guessed iConnect/BLE writes are permitted.

Authoritative device families include FRITZ! Smart Home, TP-Link Tapo, Logitech C920/UVC, Mars Hydro/iFresh targets and experimental DF100M BLE diagnostics.

## 6. Camera architecture

The generic UVC backend stays model-independent. `app/camera_policy.py` applies GrowCentral policy from the canonical hardware profile. This allows Pi 3 to stay conservative while Pi 4/5 are no longer artificially capped by the Legacy/Lite baseline.

## 7. Diagnostics

Diagnostics must expose:

- Raspberry Pi model;
- active support class and runtime profile;
- build/version;
- services, networking and radio state;
- display/kiosk state;
- setup/first-boot state;
- cloud-link state where applicable.

Support bundles and future telemetry must preserve this hardware context.

## 8. Local and cloud responsibility

Local SQLite/configuration retains enough state for independent operation. Cloud V7 is optional and provides centralized management, device/customer/group assignments, entitlements, diagnostics and remote views. The cloud never becomes an implicit local master.

## 9. Network and security boundaries

- no direct public exposure of local GUI ports;
- outbound HTTPS for cloud communication;
- remote commands are requests validated locally;
- setup AP/captive portal for first boot;
- device writes deny-by-default;
- dedicated service accounts, firewall, audit and protected secrets.

## 10. UI architecture

GrowCentral Nexus UI is shared by local GUI, kiosk, mobile and public presentation. Visual complexity may be reduced by the Legacy/Lite profile, while Pi 4/5 retain the Full-Support interface baseline.

## 11. Validation architecture

CI validates classifier behavior and generic runtime correctness. Real hardware validation is tracked by support class. A Pi-3 Legacy/Lite regression does not automatically invalidate Pi-4/5 Full Support, but must remain explicitly documented.

See [`HARDWARE_SUPPORT_POLICY.md`](HARDWARE_SUPPORT_POLICY.md) and [`HARDWARE_TEST_PLAN.md`](HARDWARE_TEST_PLAN.md).
