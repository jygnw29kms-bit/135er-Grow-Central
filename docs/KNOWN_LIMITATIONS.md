# Known Limitations and Open Risks

## Hardware support classes

- Raspberry Pi 3B/3B+ is **Legacy/Lite**, not the performance baseline for new features.
- Pi 3 is intentionally constrained to conservative camera, kiosk, diagnostics and worker defaults.
- Pi 4/400/5 are the Full-Support feature baseline; Full-Support behavior still requires real hardware validation.
- Unknown ARM hardware is `UNCLASSIFIED` and receives conservative defaults without a support guarantee.
- The project deliberately keeps one universal image; a future split is allowed only if kernel/package/service requirements diverge materially.

## Validation status

- Build 176 is the last published Candidate before the hardware-profile runtime.
- current `master` contains Post-176 runtime changes and therefore requires a fresh universal-image build before a new Candidate can be named.
- successful CI/image builds do not replace physical validation.
- validation is tracked separately by support class.

## Camera

- Pi 3 Legacy/Lite is capped by policy at 1280×720 with a reduced FPS target.
- Pi 4/5 Full Support may expose up to 1920×1080 only when the attached UVC camera actually advertises the mode.
- LED/V4L2 writes remain capability-aware and deny-by-default.

## DF100M / Mars Hydro

- DF100M protocol write details remain experimental unless reproduced on hardware;
- unverified BLE/iConnect writes remain disabled;
- Mars Hydro/iFresh integration continues to separate architecture from validated write protocol.

## Application runtime

- not every planned resource profile is yet consumed by every subsystem; `shared/hardware_profile.py` is now the required source for future profile-aware changes;
- production RBAC, backup/restore and some advanced automation/history targets remain under development;
- Cloud V7 remains optional and must never become the implicit local master.

## Test image

- public test credentials are intentionally temporary/insecure where still used by the candidate image;
- setup AP, WLAN handover, Kiosk, camera and integrations require class-specific physical testing;
- carrier-dependent Compute Module WLAN/Bluetooth/Ethernet support depends on actual carrier hardware.

## Documentation rule

Historical build documents may contain older candidate numbers or Pi-3-focused terminology. They are historical evidence only. Current operational truth is defined by `RELEASE_STATE.md`, `HARDWARE_SUPPORT_POLICY.md`, `PROJECT_STATUS.md` and the active runtime classifier.
