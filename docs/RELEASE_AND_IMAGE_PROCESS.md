# Release and Raspberry Pi Image Process

**Current version:** `alpha-0.7.5`  
**Current master anchor:** `e339602`  
**Next hardware-test candidate:** **Build 118** / `pi-universal-alpha-0.7.5-118`  
**Canonical state:** [`../RELEASE_STATE.md`](../RELEASE_STATE.md)

## Active image builder

The active universal Raspberry Pi image workflow is:

```text
.github/workflows/build-pi3-image.yml
```

It builds on Raspberry Pi OS Lite 64-bit / Debian 13 (trixie), verifies the pinned base-image SHA-256, installs Grow Central, performs image checks and writes the GitHub Actions run number into `/opt/135er-grow-central/BUILD`.

## Trigger policy

The workflow supports `workflow_dispatch` and path-based builds for runtime/image inputs such as `app/**`, `shared/**`, `web/**`, `requirements.txt`, `image-builder/brand/**` and `image-builder/firstboot/**`.

Documentation, website and Mobile-only updates do not justify a new multi-gigabyte Pi image by themselves.

## Build 117 → 118

Build 117 was successfully tested. The subsequent e339 consolidation adds runtime-relevant camera LED capability logic plus the current camera/GUI/network/FRITZ/Tapo/Elecrow state, making Build 117 superseded for the next test.

Build 118 is therefore the intended next hardware-test candidate. It must remain tied to the intended runtime state and must not be replaced by an artificial Build 119 simply because documentation or public presentation changed afterward.

## Build 118 validation

Before promotion to `VALIDATED`:

1. fresh boot and reboot;
2. setup AP / DHCP / DNS;
3. LAN/WLAN and mDNS;
4. first-boot transition and GUI availability;
5. persistence;
6. Logitech C920/UVC, snapshot, MJPEG and V4L2;
7. firmware/model/USB-ID-aware LED capability detection;
8. LED writes only where support is actually reported;
9. Elecrow kiosk if target display is present;
10. affected FRITZ!/Tapo/Mars paths;
11. support bundle on any deviation.

## Safety

Unverified device writes remain deny-by-default. In particular, DF100M/Mars Hydro reverse-engineering writes must not be enabled merely because an image build succeeds.

Temporary image credentials are test-only and must be replaced by first-boot provisioning before normal use.

## Artifact rule

The release image and its checksum belong in GitHub Actions / prerelease assets, not normal Git history. A release is only called validated when source state, image artifact, checksum and real target-hardware result are unambiguously matched.

See also: [Build 118 Release Notes](RELEASE_NOTES_BUILD_118.md) · [Release Pipeline](RELEASE_PIPELINE.md) · [Project Status](PROJECT_STATUS.md).
