# Release and Raspberry Pi Image Process

## Current image builder

The only active Raspberry Pi image workflow is:

```text
.github/workflows/build-pi3-image.yml
```

The obsolete v1 workflow was removed in v0.6 to prevent expensive image builds from running automatically after unrelated application changes.

## Trigger policy

The v2 image builder is primarily manual (`workflow_dispatch`). A change to the v2 workflow file itself can also trigger a validation build.

Ordinary changes to the website, documentation, app or tests do **not** automatically rebuild a multi-gigabyte Raspberry Pi image.

## Base image

Raspberry Pi OS Lite 64-bit / Debian 13 is used for the Pi 3B/3B+ test image. The downloaded base image is verified against its configured SHA-256 before customization.

## Historical build lessons

### v1 root filesystem exhaustion

The first builder copied build artifacts into the mounted target filesystem and filled the root partition. The corrected builder expands the image and excludes base/work image files from rsync.

### v2 UFW in ARM chroot

UFW failed inside the GitHub Actions ARM chroot because it could not determine the iptables environment. The corrected v2 workflow installs a first-boot firewall service so UFW is initialized against the real Raspberry Pi kernel.

## Test-image safety

The current hardware-test image intentionally uses temporary test credentials and must not be treated as production-ready. DF100M writes and remote cloud commands remain disabled by default.

Future production images must replace temporary credentials with a first-boot provisioning flow.
