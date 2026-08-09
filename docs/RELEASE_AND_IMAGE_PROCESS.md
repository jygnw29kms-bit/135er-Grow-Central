# Release & Raspberry Pi Image Process

## Objective

Build a reproducible, flashable Raspberry Pi image without manually modifying SD cards.

## Current image target

```text
Raspberry Pi OS Lite 64-bit
Debian 13 / Trixie based
Raspberry Pi 3B/3B+ target
```

The workflow downloads a pinned official Raspberry Pi OS image and verifies its SHA256 before customization.

## Installed test-image components

- current 135er GrowControl repository snapshot;
- Python virtual environment and project dependencies;
- BlueZ/Bluetooth tooling;
- OpenSSH server;
- SQLite and utilities;
- unattended upgrades;
- UFW;
- dedicated `growcontrol` service account;
- systemd GrowControl service;
- first-boot firewall initialization service.

## Temporary image credentials

```text
hostname: growcontrol-test
SSH: test / test
application/API token: test
```

## Image output

Expected release assets:

```text
135er_GrowControl_RPi3B_Test.img.xz
135er_GrowControl_RPi3B_Test.img.xz.sha256
135er_GrowControl_RPi3B_Test-CREDENTIALS.txt
```

Large images belong in GitHub Releases/Actions artifacts, not normal Git history.

## Builder incident history

### Failure 1 – filesystem full

Cause: the downloaded `base.img.xz`/working image existed in the checked-out workspace and was copied into `/opt/135er-growcontrol` during `rsync`.

Fix:

- exclude `.img`, `.img.xz`, `base.img*`, `work.img*`;
- grow image by 2 GiB;
- expand partition 2 and ext filesystem before customization.

### Failure 2 – UFW in chroot

Cause:

```text
ERROR: Couldn't determine iptables version
```

The ARM chroot under GitHub Actions cannot reliably initialize UFW against the runner/kernel environment.

Fix: create `growcontrol-firstboot-firewall.service`, executed on the physical Pi before GrowControl. It applies:

```text
default deny incoming
default allow outgoing
allow 22/tcp
allow 8080/tcp
```

and writes a marker so initialization is one-time.

## Release quality gate

A test-image prerelease should only be promoted after:

1. GitHub build success;
2. checksum generated;
3. image flash succeeds;
4. Pi boots at least twice;
5. SSH, Bluetooth and GrowControl service active;
6. UI reachable on LAN;
7. safe defaults confirmed;
8. test notes added to documentation.

## Versioning principle

Prebuilt hardware images are prereleases during protocol research. Stable semantic release tags should only be used when the documented runtime status matches tested behavior.
