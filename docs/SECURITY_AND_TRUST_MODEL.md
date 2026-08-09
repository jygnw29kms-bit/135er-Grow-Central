# Security & Trust Model

## Core assumption

135er GrowControl can eventually issue physical device commands. Therefore protocol uncertainty, remote access and account privileges must be treated as safety boundaries, not merely UX concerns.

## Trust zones

### Zone 1 – Local Raspberry Pi
Highest operational authority. Owns device adapter, local state and final command validation.

### Zone 2 – Local browser/tablet
Trusted only after application authentication is implemented; during early hardware tests the LAN itself must not be treated as globally trusted.

### Zone 3 – Optional VPS cloud
May store telemetry/history and request remote commands, but cannot bypass local validation.

### Zone 4 – Vendor ecosystem / internet
External dependency. Not trusted as a requirement for local operation.

## Default-deny behaviors

```text
DF100M_ALLOW_WRITES=false
GC_REMOTE_COMMANDS=false
GC_CLOUD_ENABLED=false
```

These defaults are intentional.

## Test credentials

The Pi test image currently uses:

```text
username: test
password: test
token: test
```

This is only acceptable for short-lived isolated hardware testing. Before connecting to an untrusted/shared network:

- change password;
- replace tokens;
- remove passwordless sudo for the test user;
- review SSH configuration;
- prefer proper application login/RBAC when available.

## Network rules

- Never port-forward Pi:8080 directly to the internet.
- Use outbound HTTPS from Pi to optional cloud.
- VPS should terminate TLS through Nginx or equivalent reverse proxy.
- Firewall and Fail2ban are part of server hardening baseline.
- Pi test image initializes UFW on first real boot because chroot initialization is unreliable.

## Remote command model

A cloud command is a **request**, not direct actuator access. Pi validates:

- target device/site;
- action type;
- allowed value range;
- local remote-command enable flag;
- local device/write safety state.

## Protocol safety

Unvalidated BLE payloads must not be generalized into automatic control. Evidence progression:

```text
candidate → observed → replayed → validated
```

## Secrets

Secrets belong in environment/configuration files with restricted permissions. Do not commit real API tokens, passwords, private keys or cloud credentials.

## RBAC target

- Admin: full platform/user/system/device authority.
- Operator: operational control, schedules and automations.
- Viewer: read-only dashboard/sensor/history access.
- Device/Agent: restricted telemetry/status/command channel.

The RBAC target is defined, but full production enforcement must be verified in runtime before claiming completion.

## Audit target

Security-relevant changes should produce audit records including actor, action, target, timestamp and outcome. This remains part of platform implementation work.
