# 135er-Grow Central – Full Platform Baseline v0.5

## Supported systems

Supported target platforms:

- Debian 12
- Debian 13
- Ubuntu Server 22.04 LTS
- Ubuntu Server 24.04 LTS
- Raspberry Pi OS 64-bit based on Debian

Other distributions are initially unsupported.

## System roles

### Local Node / Raspberry Pi

The Pi remains the master for:

- BLE device communication
- local sensors
- local schedules
- local automation
- fail-safe behavior
- local history/buffering
- cloud synchronization

Loss of Internet or VPS must not stop local rules.

### Cloud Node / VPS

The VPS optionally provides:

- users and roles
- remote dashboard
- long-term history
- multi-site support
- alerts
- audit log
- remote-command queue
- central backups/exports

## Services

```text
Raspberry Pi
├── grow-central-local.service
├── grow-central-cloud-link.service
├── BlueZ
├── SQLite
└── systemd

VPS
├── Nginx
├── Grow Central Cloud API
├── PostgreSQL
├── Fail2ban
├── firewall
├── Certbot / ACME
└── systemd or Docker Compose
```

## Installer

The installer must:

1. validate OS and version,
2. update APT metadata,
3. install required packages,
4. create the dedicated `grow-central` system user,
5. create directories and permissions,
6. create a Python venv,
7. place config in `/etc/135er-grow-central`,
8. place runtime data in `/var/lib/135er-grow-central`,
9. log through journald,
10. install systemd units,
11. optionally enable firewall/Fail2ban,
12. for cloud: configure domain, Nginx and TLS,
13. perform health checks.

## APT/OS hardening

Planned:

- `unattended-upgrades`
- `apt-listchanges`
- regular `apt update`
- controlled `apt full-upgrade`
- `apt autoremove`
- automatic security updates
- traceable service restarts

## File permissions

Recommended:

```text
/opt/135er-grow-central       root:grow-central 0750
/etc/135er-grow-central       root:grow-central 0750
/var/lib/135er-grow-central   grow-central:grow-central 0750
```

Secrets use 0640 or stricter.

## Network and domain

Public cloud access only over HTTPS:

```text
Internet
  │
  ▼
TCP 443
  │
Nginx
  │
Grow Central Cloud API
  │
PostgreSQL internal only
```

Do not expose publicly:

- PostgreSQL
- local Pi API
- Docker internal ports
- debug endpoints

## Data storage

Local: SQLite.

Cloud: PostgreSQL.

Details: `docs/en/DATABASE_AND_RBAC.md`.

## Remote commands

A remote command may execute only if:

1. the cloud server permits remote commands,
2. the specific local node permits remote commands,
3. the user/role owns the required permission,
4. the command has not expired,
5. target device and value range are validated locally.

## Fail-safe

During cloud outage:

- local UI remains available,
- schedules continue,
- automation continues,
- sensors continue to be stored,
- telemetry is buffered locally,
- synchronization resumes later.
