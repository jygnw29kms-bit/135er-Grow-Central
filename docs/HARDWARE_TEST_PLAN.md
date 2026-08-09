# Hardware Test Plan – Raspberry Pi 3B + DF100M

## Purpose

Provide a repeatable, low-risk procedure for the first physical validation of 135er-Grow Central.

## Preconditions

- Raspberry Pi 3B or 3B+
- reliable power supply
- microSD card
- Ethernet preferred for first test; Wi-Fi may be configured separately
- DF100M powered and reachable by BLE
- Mars Legacy app available for comparison
- test environment isolated from untrusted networks while temporary `test/test` credentials are used

## Phase A – Image validation

1. Download `135er-Grow-Central_RPi3B_Test.img.xz` from GitHub prerelease.
2. Verify SHA256 against accompanying checksum.
3. Flash using Raspberry Pi Imager or balenaEtcher.
4. Boot with Ethernet connected.
5. Confirm hostname `grow-central-test`.
6. SSH with `test/test`.
7. Immediately record IP address and boot timestamp.

### Acceptance criteria

```bash
systemctl is-active ssh
systemctl is-active bluetooth
systemctl is-active 135er-grow-central.service
systemctl status grow-central-firstboot-firewall.service
```

Expected local UI:

```text
http://<PI-IP>:8080
```

## Phase B – Security/bootstrap validation

Check:

```bash
sudo ufw status verbose
```

Expected incoming allowances: SSH/22 and Grow Central/8080 only for current test baseline.

Confirm:

```text
DF100M_ALLOW_WRITES=false
GC_REMOTE_COMMANDS=false
GC_CLOUD_ENABLED=false
```

Do not expose the Pi directly to the public internet.

## Phase C – Bluetooth validation

```bash
bluetoothctl
power on
scan on
```

Record all DF100M-related advertisement names/addresses. Stop Mars Legacy completely before Grow Central connection testing.

Use Grow Central:

```text
GET  /api/discover
POST /api/connect
GET  /api/services
POST /api/notify/start
```

Record service UUIDs, characteristic UUIDs, properties and notifications.

## Phase D – Legacy correlation

Using the Legacy app, execute controlled values:

```text
10 %
30 %
50 %
70 %
90 %
```

For each value capture:

- timestamp;
- setpoint;
- fan audible/physical response;
- BLE notifications;
- changed payload bytes;
- RPM if exposed;
- reconnect behavior.

## Phase E – Controlled replay

Only after a consistent candidate is identified:

1. set `DF100M_ALLOW_WRITES=true` temporarily;
2. start with low/non-destructive value;
3. send one candidate payload;
4. observe response;
5. disable writes immediately after test;
6. repeat only after reviewing evidence.

Never run uncontrolled loops during initial protocol validation.

## Test record template

| Test | Input | UUID | Payload | Notification | Physical result | Evidence level |
|---|---|---|---|---|---|---|
| H01 | discover | n/a | n/a | n/a | device visible | observed |
| H02 | connect | service | n/a | n/a | connected | observed |
| H03 | 10% Legacy | TBD | TBD | TBD | TBD | observed |

## Exit criteria for first milestone

The first milestone is successful when:

- Pi image boots reliably;
- local service and UI survive reboot;
- Bluetooth adapter is operational;
- DF100M can be discovered and inspected;
- notification data can be captured;
- no accidental writes occur with safe defaults.

Validated speed control is a later exit criterion, not required for first boot success.
