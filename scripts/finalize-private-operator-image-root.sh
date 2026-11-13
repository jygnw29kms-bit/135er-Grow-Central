#!/usr/bin/env bash
# Finish an existing private operator image on the owner-controlled root server.
# Prompts on the ROOT console; never logs or stores a plaintext password on disk.
set -Eeuo pipefail
umask 077
[[ $EUID -eq 0 ]] || { echo "Execute as root on the operator server" >&2; exit 2; }
IMAGE="${1:-/var/tmp/gc-operator-build/135er-GrowCentral-Operator-2026-11-12.img}"
TARGET="${2:-/srv/JL1976/Grow-Central/Operator-Images}"
[[ -f "$IMAGE" && "$IMAGE" == *.img && -d "$TARGET" ]] || {
  echo "Expected uncompressed prepared operator image and private target directory" >&2; exit 2;
}
[[ -s /var/tmp/gc-operator-build/src/.git/HEAD ]] || {
  echo "Builder source not available" >&2; exit 2;
}
SOURCE=/var/tmp/gc-operator-build/src
git -C "$SOURCE" fetch --quiet origin master
git -C "$SOURCE" checkout -q master
git -C "$SOURCE" merge --ff-only -q origin/master
CHECKOUT_SHA="$(git -C "$SOURCE" rev-parse HEAD)"
for path in \
  scripts/patch-private-operator-image-access.sh \
  image-builder/firstboot/gc-firstboot-maintenance-provision.sh \
  scripts/install-gc-maintenance-agent.sh; do
  [[ -s "$SOURCE/$path" ]] || exit 3
  bash -n "$SOURCE/$path"
done
python3 -m unittest discover -s "$SOURCE/tests" -p test_private_operator_fixed_access.py

# Explicitly gather the stable TEST credential from /dev/tty, not from shell
# history, command-line args, GitHub, or the assistant's command transcripts.
[[ -r /dev/tty ]] || { echo "An interactive root console is required" >&2; exit 4; }
printf 'Fixed gc-maint TEST password: ' >/dev/tty
IFS= read -r -s operator_password </dev/tty
printf '\n' >/dev/tty
[[ "${#operator_password}" -ge 12 ]] || {
  echo "Password too short, refusing image changes" >&2; exit 4;
}
# Temporary password input is memory-backed, root-only, automatically removed.
pass_file="$(mktemp /run/grow-central-operator-password.XXXXXXXX)"
chmod 0600 "$pass_file"
cleanup() {
  set +e
  unset operator_password
  if [[ -n "${pass_file:-}" ]]; then rm -f "$pass_file"; fi
}
trap cleanup EXIT
printf '%s' "$operator_password" >"$pass_file"
unset operator_password
bash "$SOURCE/scripts/patch-private-operator-image-access.sh" "$IMAGE" "$pass_file"
rm -f "$pass_file"
pass_file=""
NEW_IMAGE="${IMAGE%.img}-fixed-maintenance.img"
[[ -s "$NEW_IMAGE" ]] || exit 5

# Read-only mounted-contents checks performed before final packaging.
audit_root="$(mktemp -d /tmp/gc-operator-final-audit.XXXXXXXX)"
loop=""
audit_cleanup() {
  set +e
  mountpoint -q "$audit_root" && umount "$audit_root"
  [[ -n "$loop" ]] && losetup -d "$loop"
  rmdir "$audit_root" 2>/dev/null || :
}
trap 'cleanup; audit_cleanup' EXIT
loop="$(losetup --find --show --partscan --read-only "$NEW_IMAGE")"
mount -o ro "${loop}p2" "$audit_root"
test -s "$audit_root/etc/135er-grow-central/operator-maint-password.hash"
test "$(stat -c %a "$audit_root/etc/135er-grow-central/operator-maint-password.hash")" = 600
test -s "$audit_root/opt/grow-central/mesh-agent/meshagent.msh"
test -x "$audit_root/opt/grow-central/mesh-agent/meshagent"
test -x "$audit_root/usr/local/sbin/gc-firstboot-maintenance-provision"
grep -Fq 'MAINTENANCE_SUDO_VERIFIED=UID_0' "$audit_root/opt/135er-grow-central/scripts/install-gc-maintenance-agent.sh"
grep -Fxq 'NoNewPrivileges=no' "$audit_root/etc/systemd/system/grow-central-firstboot-maintenance.service"
for u in ssh.service grow-central-mesh-agent.service grow-central-firstboot-maintenance.service; do
  test -L "$audit_root/etc/systemd/system/multi-user.target.wants/$u"
done
test -L "$audit_root/etc/systemd/system/timers.target.wants/grow-central-remote-watchdog.timer"
test ! -e "$audit_root/home/gcmaint/.ssh/authorized_keys"
umount "$audit_root"
losetup -d "$loop"
loop=""
rmdir "$audit_root"
echo "OFFLINE_PRIVILEGED_IMAGE_AUDIT=PASS"

# Archive + checksums, always within owner-only folder; no public upload.
name="135er-GrowCentral-Operator-FixedSudo-$(date -u +%Y%m%d)-${CHECKOUT_SHA:0:12}.img.xz"
[[ ! -e "$TARGET/$name" ]] || { echo "Target already exists" >&2; exit 6; }
archive_tmp="$(mktemp "$TARGET/.grow-central-partial.XXXXXXXX.xz")"
archive_cleanup() {
  set +e
  [[ -n "${archive_tmp:-}" ]] && rm -f -- "$archive_tmp"
}
trap 'cleanup; audit_cleanup; archive_cleanup' EXIT
nice -n 10 xz -T2 -2 -c "$NEW_IMAGE" > "$archive_tmp"
chmod 0600 "$archive_tmp"
xz -t "$archive_tmp"
mv -n "$archive_tmp" "$TARGET/$name"
archive_tmp=""
(cd "$TARGET"; sha256sum "$name" > "$name.sha256"; sha256sum -c "$name.sha256")
chmod 0600 "$TARGET/$name.sha256"
echo "PRIVATE_IMAGE_READY=$TARGET/$name"
echo "SHA256=$(sha256sum "$TARGET/$name" | cut -d' ' -f1)"
echo "MAINTENANCE_LOGIN=gc-maint; ROOT_SUDO=firstboot_uid0_probe; MCP_AGENT=bundled"
echo "PI_HARDWARE_BOOT_TEST=PENDING"
