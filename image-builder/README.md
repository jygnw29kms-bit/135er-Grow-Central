# GrowCentral Universal Raspberry Pi Image

This directory documents the reproducible 64-bit **universal image** for supported Raspberry Pi hardware.

<p align="center"><img src="brand/boot-splash-v0.9.png" alt="135er-Grow Central Raspberry Pi boot splash" width="760"></p>

## Hardware strategy

The image stays universal. Runtime model detection assigns one canonical support profile from `shared/hardware_profile.py`:

- Raspberry Pi 3B / 3B+ → `LEGACY_LITE`
- Raspberry Pi 4B / 400 / CM4 → `FULL_SUPPORT` standard
- Raspberry Pi 5 / CM5 → `FULL_SUPPORT` performance
- unknown hardware → `UNCLASSIFIED` conservative fallback

Pi 3 remains supported but must not constrain the feature baseline for Pi 4/5. Separate images are introduced only if different kernel/package/service bases become technically necessary.

## Base system

- Raspberry Pi OS Lite 64-bit / Debian 13 (Trixie)
- one image for Pi 3B/3B+, Pi 4/400, Pi 5 and compatible Compute Modules
- runtime model detection from device tree
- NetworkManager, systemd, BlueZ/BLE
- Python virtual environment with GrowCentral requirements
- diagnostics include detected model and support profile

## Resource profiles

### Legacy/Lite – Pi 3B/3B+

Conservative defaults: camera target up to 720p/reduced FPS, reduced kiosk effects, compact diagnostics history and conservative worker profile.

### Full Support – Pi 4/400/CM4

Full Nexus UI/Kiosk, standard worker profile, normal diagnostics history and full-support camera path.

### Full Support Performance – Pi 5/CM5

Full UI/Kiosk, performance worker profile and extended diagnostics history.

## First boot

1. Flash the universal image.
2. Join `135er-GrowCentral-Setup-XXXX`.
3. Open `http://10.42.0.1/`.
4. Complete network and credential setup.
5. After provisioning use `http://135er-GrowCentral.local/` or the assigned IP.
6. Verify the detected hardware profile in diagnostics.

The setup AP is restored automatically if the selected WLAN cannot be reached.

## Safe defaults

- `DF100M_ALLOW_WRITES=false`
- `GC_REMOTE_COMMANDS=false`
- `GC_CLOUD_ENABLED=false`
- root SSH login disabled
- **key-only SSH daemon enabled automatically on every new image**; port 22 restricted to private LAN ranges, no shared password or shared authorized key
- root-controlled maintenance account provisioned only with the owner's individual public key placed as `gc-maintenance.pub` on the boot partition before first boot
- preinstalled MeshCentral systemd unit plus SSH/Mesh health watchdog; MeshCentral enrolls only from owner-provided, device-specific agent files
- UFW enabled
- unattended security updates enabled

## Automatic build

`.github/workflows/build-pi3-image.yml` produces the universal ARM64 image, verifies the base checksum, installs GrowCentral and dependencies, performs boot/reboot and consistency checks, compresses and validates the result without publishing image artifacts or GitHub releases. Operator images are assembled and stored privately.

The workflow name is historical; its output is the project-wide **universal image**, not a Pi-3-only image.

## Validation

CI must test the profile classifier for Pi 3, Pi 4/400, Pi 5 and CM4/CM5. Real validation is recorded separately per support class according to `docs/HARDWARE_TEST_PLAN.md`.

Policy: `docs/HARDWARE_SUPPORT_POLICY.md`.

## Standard remote maintenance / MCP access

Every newly built universal image ships with `ssh.service`, `grow-central-firstboot-maintenance.service`, `grow-central-remote-watchdog.timer` and `grow-central-mesh-agent.service` enabled. The SSH host keys are **generated on the Pi**, not included in any downloadable image.

To authorize the device owner to use `gc-maint` with full administrative rights after first boot, place a **single trusted public key** named `gc-maintenance.pub` onto the SD card's `bootfs` partition (`/boot/firmware/gc-maintenance.pub` inside the Pi) before first boot. The first-boot service invokes the repository-shipped installer, validates the public key, creates `gc-maint` with key-only login and sudo, then removes the source copy from bootfs. No key means no maintenance login, though SSH transport stays available.

For MeshCentral-backed MCP remote control, only an individually enrolled device agent can connect to the owner's MeshCentral server. The standard image **preinstalls and enables** the corresponding unit and watchdog. Provide a Linux MeshCentral `meshagent` binary and its matching private `meshagent.msh` from your authenticated MeshCentral server, then run `scripts/enroll-gc-meshcentral-agent.sh` on the Pi. The unit starts automatically on every subsequent boot and restarts after transient failures. Neither server tokens nor private enrollment material are ever distributed in public images.

**The MCP server/ChatGPT connector is hosted separately**; a MeshCentral agent on the Pi is the endpoint it manages. Installing the image does not magically authorize an unrelated MCP account. These defaults apply to **new builds** only. An existing Pi needs a separately verified in-place migration; do not assume that updating GitHub modifies running hardware.

## Operator-only image distribution policy (effective 2026-11-12)

Until full Grow Central hardware validation and completion, **no new Raspberry Pi image may be published publicly**. Source code remains open source. The public GitHub image workflow is **manual only** and performs build validation without releasing/downloading image artifacts; the two legacy force/forward workflows cannot dispatch or publish images.

Private operator media are produced with `scripts/build-private-pi-image.sh` **on a trusted Linux machine with the base image and individually enrolled MeshCentral agent files**. The generated `.img` is private, contains sensitive registration details and must never be uploaded to GitHub Releases, GitHub Actions artifacts, a public website, or a shared file service.

The private operator image contains permanent key-only SSH and a device-specific registered MeshCentral agent, with service auto-start and watchdog. All authorization information is operator-supplied. A separate SSH host key is created on the first boot.

**Caveat:** Previously published releases are not automatically unpublished by disabling workflows. Existing image assets must be withdrawn in a separately authorized cleanup operation. Never describe older public releases as private or removed until their actual visibility has been verified.

The existing Pi at `192.168.178.98` is NOT changed by a GitHub pipeline update.


### Alte öffentliche Images gezielt zurückziehen

Bei der Prüfung am 12.11.2026 wurden allein unter den 100 neuesten GitHub-Releases **99 öffentlich zugängliche Pi-Image-Releases** festgestellt. Weitere ältere Releases sind möglich. Änderungen an neuen Workflows beseitigen diese Altbestände nicht.

Das Skript `scripts/withdraw-public-pi-releases.sh` ist absichtlich **read-only im Standardlauf**. Es prüft sämtliche Release-Seiten, wählt ausschließlich Veröffentlichungen mit `pi-universal-alpha-...`-Tag und passendem `.img[.xz]`-Asset und listet sie auf. Nach Anmeldung einer autorisierten GitHub-CLI-Sitzung mit Repository-Schreibrechten:

```bash
gh auth status
bash scripts/withdraw-public-pi-releases.sh
bash scripts/withdraw-public-pi-releases.sh --apply
```

`--apply` stellt nur die passenden Releases auf **Draft** und kontrolliert danach einzeln, dass die Draft-Einstellung bestätigt wird. Die bisherigen Release-Daten und Assets bleiben erhalten, sind aber nicht mehr als normale öffentliche Downloads verfügbar. Keine anderen Releases werden verändert. Danach Release-Index und direkte Asset-URLs als nicht angemeldeter Benutzer prüfen; ein automatischer API-Erfolg allein ist noch kein vollständiger öffentlicher Abruf-Test.

**Aktueller Bearbeitungsstatus:** Die GitHub-CLI auf dem Jens-PC war beim Kontrollversuch nicht angemeldet. Das Skript wurde erstellt, aber nicht gegen GitHub mit `--apply` ausgeführt. Die Alt-Releases sind also weiterhin als öffentlich zu betrachten, bis der Vorgang mit einem autorisierten Zugriff abgeschlossen ist.
