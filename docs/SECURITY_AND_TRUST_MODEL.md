# Security and Trust Model – 135er-Grow Central alpha-0.7.1

## Objective

Compromise of an IoT device, cloud account, browser session or third-party integration must not automatically grant unrestricted control over the Raspberry Pi or every connected device.

## Trust zones

1. Grow Central Core – highest trust.
2. Authenticated admin/operator client.
3. Home Assistant / MQTT – explicit integration trust.
4. IoT devices – untrusted network peers by default.
5. Optional cloud – never authoritative for local safety.
6. Internet – untrusted.

## Current controls

- smart-home writes disabled globally by default;
- DF100M writes disabled by default;
- raw DF100M writes require a separate explicit opt-in;
- active BLE scans, connection changes and GATT diagnostics require local authentication;
- missing local write token causes protected commands to fail closed;
- explicit device inventory;
- explicit `approved` and `writable` flags;
- restricted adapter factory;
- Shelly and onboarding targets restricted to usable private/link-local literal IPv4 addresses;
- Home Assistant connector limited to registered `switch.*` entities;
- Home Assistant read-only mode enabled by default;
- no arbitrary URL proxy;
- no arbitrary Home Assistant service proxy;
- append-only JSONL audit events for smart-home writes;
- credentials referenced through server-side environment variables only.

## Default environment

```text
DF100M_ALLOW_WRITES=false
DF100M_ALLOW_RAW_WRITES=false
GC_REMOTE_COMMANDS=false
GC_CLOUD_ENABLED=false
GC_SMARTHOME_ENABLED=false
GC_HA_READ_ONLY=true
GC_LOCAL_API_TOKEN=
```

## Production secrets

Recommended file:

```text
/etc/135er-grow-central/secrets.env
owner root
group growcentral
mode 0640
```

Production credentials must never use `test`, `CHANGE_ME` or values committed to Git.

## Network guidance

Recommended topology separates trusted clients and IoT devices where possible. The Pi should be permitted to reach configured local device endpoints, while unsolicited IoT-to-trusted-LAN traffic is blocked. The local GUI ports 80 and 8080 must not be exposed directly to the public internet.

## Remaining security work

- full user/session authentication;
- RBAC enforcement in runtime;
- CSRF protection for cookie-authenticated writes;
- login rate limiting;
- stronger systemd filesystem/capability sandboxing;
- encrypted/managed secret backend;
- formal audit database and retention policy;
- recovery/rollback tests.
