# Hardware Test Plan – Raspberry Pi 3B + Mars Hydro/iConnect

## Purpose

Provide a repeatable, low-risk procedure for physical validation of 135er-Grow Central while keeping the project clearly in Alpha.

## Authoritative target hardware

- Raspberry Pi 3B / 3B+
- **Mars Hydro FC3000, model year 2024, USB port, iConnect support**
- **Mars Hydro iFresh / DF100 series using iConnect**
- DF100M / `MZ_MZF002` only as experimental BLE diagnostics/fallback
- Logitech C920 camera
- supported smart-home/power targets: Shelly, TP-Link Tapo, FRITZ!SmartHome, Home Assistant
- **no ESP32 in the target architecture**

## Current Alpha observation

The current image has been reported to behave well in its **first basic functions from first boot**. Record this as a positive smoke-test result only. Repeatability and all physical device paths below remain to be validated.

## Phase A – Fresh image / first-boot validation

1. Flash the current published `135er-Grow-Central` Raspberry Pi 3B Alpha image to a clean microSD card.
2. Boot without manual filesystem or configuration edits.
3. Confirm that boot proceeds without an indefinite setup/Bluetooth dependency block.
4. Confirm the setup AP appears when provisioning is required.
5. Confirm a client receives an address from the dedicated `10.42.0.0/24` provisioning network.
6. Open the setup portal and verify authentication.
7. Verify WLAN list, hostname, timezone and password setup.
8. Complete provisioning and confirm the main GUI becomes reachable.
9. Reboot and confirm the main GUI returns without manual repair.

### Acceptance criteria

- first boot completes without manual intervention;
- AP/DHCP works when required;
- the local service is reachable on port 8080;
- the provisioning marker is only committed after successful setup;
- a failed setup does not permanently block the main GUI;
- watchdog/recovery does not enter a restart loop;
- reboot remains healthy.

Useful checks:

```bash
systemctl is-active ssh
systemctl is-active bluetooth
systemctl is-active 135er-grow-central.service
curl -fsS http://127.0.0.1:8080/api/health
```

## Phase B – Security/bootstrap validation

Confirm that sensitive write and cloud paths remain disabled unless explicitly enabled for a controlled test:

```text
DF100M_ALLOW_WRITES=false
DF100M_ALLOW_RAW_WRITES=false
GC_REMOTE_COMMANDS=false
GC_CLOUD_ENABLED=false
```

Do not expose the Raspberry Pi service directly to the public internet. Public website, optional cloud and local control remain separate trust zones.

## Phase C – Bluetooth diagnostics validation

The BLE path is no longer the primary Mars-Hydro architecture. It is used only for diagnostics/reverse engineering/fallback.

Verify:

- Bluetooth is powered automatically;
- advertised device names are shown when available;
- generic devices are not falsely identified as Mars Hydro;
- likely `MZ_MZF002` / iFresh-related advertisements are marked as diagnostics candidates;
- connection and GATT inspection work without guessed writes.

Relevant local endpoints:

```text
GET  /api/discover
POST /api/connect
GET  /api/services
POST /api/notify/start
```

## Phase D – Mars Hydro FC3000 2024 / iConnect observation

With the exact target lamp:

1. identify how the 2024 FC3000 USB/iConnect interface enumerates or communicates in normal supported use;
2. record device identity, interface, state transitions and any locally observable traffic;
3. compare off/on and known dim levels;
4. document whether local communication is possible without vendor cloud dependency;
5. do not implement or send guessed commands.

Record at minimum:

- exact hardware/revision information;
- connection/interface type;
- iConnect behavior;
- readable state;
- dimming/state changes;
- reconnect behavior;
- behavior after Raspberry Pi reboot or temporary link loss.

## Phase E – Mars Hydro iFresh / DF100 observation

Repeat the same evidence-driven process for the iFresh/DF100 series:

- identity and pairing behavior;
- iConnect communication path;
- power/fan state;
- speed levels;
- modes/schedules if actually exposed;
- reconnect and failure behavior.

Only use the existing DF100M BLE tooling when it provides useful diagnostics. It must not silently substitute for a validated iConnect path.

## Phase F – Controlled BLE replay, only if needed

Only after a consistent BLE candidate is observed from real device/app behavior:

1. enable writes temporarily;
2. use a low-risk known command/value;
3. send one candidate payload;
4. observe and document the response;
5. disable writes immediately after the test;
6. repeat only after reviewing evidence.

Never run uncontrolled write loops during protocol research.

## Phase G – Logitech C920

Verify:

```bash
v4l2-ctl --list-devices
ffmpeg -f v4l2 -list_formats all -i /dev/video0
```

Confirm the Grow Central service account has access through the `video` group and that camera initialization does not block the main UI.

## Phase H – Smart-home / power telemetry

For each real supported device path verify:

- discovery/onboarding;
- readable name and status;
- ON/OFF state;
- W, kWh, V, A, Hz where the hardware actually exposes them;
- protected writes;
- disconnect/offline handling;
- hour/day/week/month/year history once persistent time-series is active;
- user-defined €/kWh cost projection against known reference values.

## Test record template

| Test | Device/path | Input/action | Observed state | Physical result | Recovery | Evidence |
|---|---|---|---|---|---|---|
| H01 | Pi image | fresh first boot | TBD | GUI reachable | TBD | observed |
| H02 | FC3000 2024 | identity / iConnect observation | TBD | TBD | TBD | observed |
| H03 | iFresh / DF100 | identity / iConnect observation | TBD | TBD | TBD | observed |
| H04 | DF100M BLE diagnostics | discover/GATT | TBD | no write | TBD | observed |
| H05 | C920 | enumerate/capture | TBD | video frame | TBD | observed |

## Exit criteria before Beta consideration

Beta is not reached merely because the image boots. Before a Beta designation, the project should have repeatable evidence that:

- fresh image first boot and reboot work reliably;
- setup AP/DHCP/provisioning are reproducible;
- local GUI and watchdog recovery are stable;
- FC3000 2024 and iFresh/DF100 communication paths are understood and safely implemented;
- device writes are controlled, authenticated and audited;
- Bluetooth diagnostics remain safe;
- camera and intended smart-home/power paths work on real target hardware;
- critical offline/error cases have been exercised.
