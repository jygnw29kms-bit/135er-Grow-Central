# Security and Trust Model – 135er GrowControl v0.6

## Objective

Compromise of an IoT device, cloud account, browser session or third-party integration must not automatically grant unrestricted control over the Raspberry Pi or every connected device.

## Trust zones

1. GrowControl Core – highest trust.
2. Authenticated admin/operator client.
3. Home Assistant / MQTT – explicit integration trust.
4. IoT devices – untrusted network peers by default.
5. Optional cloud – never authoritative for local safety.
6. Internet – untrusted.

## v0.6 controls

- smart-home writes disabled globally by default;
- DF100M writes disabled by default;
- missing local write token causes protected commands to fail closed;
- explicit device inventory;
- explicit `approved` and `writable` flags;
- restricted adapter factory;
- Shelly targets restricted to private/link-local literal IP addresses;
- Home Assistant connector limited to registered `switch.*` entities;
- Home Assistant read-only mode enabled by default;
- no arbitrary URL proxy;
- no arbitrary Home Assistant service proxy;
- append-only JSONL audit events for smart-home writes;
- credentials referenced through server-side environment variables only.

## Default environment

```text
DF100M_ALLOW_WRITES=false
GC_REMOTE_COMMANDS=false
GC_CLOUD_ENABLED=false
GC_SMARTHOME_ENABLED=false
GC_HA_READ_ONLY=true
GC_LOCAL_API_TOKEN=
```

## Production secrets

Recommended file:

```text
/etc/135er-growcontrol/secrets.env
owner root
group growcontrol
mode 0640
```

Production credentials must never use `test`, `CHANGE_ME` or values committed to Git.

## Network guidance

Recommended topology separates trusted clients and IoT devices where possible. The Pi should be permitted to reach configured local device endpoints, while unsolicited IoT-to-trusted-LAN traffic is blocked. Port 8080 must not be exposed directly to the public internet.

## Remaining security work

- full user/session authentication;
- RBAC enforcement in runtime;
- CSRF protection for cookie-authenticated writes;
- login rate limiting;
- stronger systemd filesystem/capability sandboxing;
- encrypted/managed secret backend;
- formal audit database and retention policy;
- recovery/rollback tests.
