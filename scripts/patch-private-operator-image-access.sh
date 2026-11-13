#!/usr/bin/env bash
# Update a private, already-personalized Pi image with a fixed sudo test password.
# No plaintext credentials in source files, terminal output, or image.
set -Eeuo pipefail
umask 077
[[ $EUID -eq 0 && $# -eq 2 ]] || {
  echo "Usage: sudo bash $0 private-operator.img /private/fixed-password-file" >&2
  exit 2
}
original="$(realpath "$1")"
password="$(realpath "$2")"
[[ -f "$original" && -f "$password" && "$original" == *.img ]] || exit 2
[[ "$(stat -c %s "$password")" -ge 12 && "$(stat -c %s "$password")" -le 256 ]] || exit 2
source_root="$(cd "$(dirname "$0")/.." && pwd -P)"
script="$source_root/image-builder/firstboot/gc-firstboot-maintenance-provision.sh"
[[ -s "$script" ]] || exit 3
target="$(dirname "$original")/$(basename "$original" .img)-fixed-maintenance.img"
[[ ! -e "$target" ]] || exit 3
cp --reflink=auto --sparse=always "$original" "$target"
chmod 0600 "$target"
work="$(mktemp -d /tmp/gc-maint-image.XXXXXXXX)"
mkdir "$work/root" "$work/boot"
root_on=0
boot_on=0
complete=0
cleanup(){
  set +e
  [[ $boot_on -eq 1 ]] && umount "$work/boot"
  [[ $root_on -eq 1 ]] && umount "$work/root"
  rmdir "$work/boot" "$work/root" "$work" 2>/dev/null || :
  [[ $complete -eq 1 ]] || rm -f -- "$target"
}
trap cleanup EXIT
# Some virtualized root servers do not create /dev/loopXp1 and p2 for
# --partscan. Mount the exact MBR partition byte ranges instead.
read -r BOOT_OFFSET BOOT_BYTES ROOT_OFFSET ROOT_BYTES < <(
  sfdisk --json "$target" | python3 -c '
import json,sys
t=json.load(sys.stdin)["partitiontable"]
parts=t["partitions"]
if len(parts)!=2:
    raise SystemExit("Expected two Raspberry Pi partitions")
sector=t.get("sectorsize",512)
print(*(v*sector for p in parts for v in (p["start"],p["size"])))
')
[[ "${BOOT_OFFSET:-}" =~ ^[0-9]+$ && "${BOOT_BYTES:-}" =~ ^[0-9]+$ &&
   "${ROOT_OFFSET:-}" =~ ^[0-9]+$ && "${ROOT_BYTES:-}" =~ ^[0-9]+$ ]] || {
  echo "Invalid image partition geometry" >&2; exit 4
}
mount -o "loop,offset=$ROOT_OFFSET,sizelimit=$ROOT_BYTES" "$target" "$work/root"
root_on=1
mount -o "loop,offset=$BOOT_OFFSET,sizelimit=$BOOT_BYTES" "$target" "$work/boot"
boot_on=1
root="$work/root"
[[ -s "$work/boot/gc-maintenance.pub" &&
   -f "$root/opt/135er-grow-central/SOURCE_COMMIT" &&
   -x "$root/opt/grow-central/mesh-agent/meshagent" &&
   -s "$root/opt/grow-central/mesh-agent/meshagent.msh" ]] || {
  echo "Missing authorized owner key or bundled MeshCentral agent" >&2; exit 4
}
hash="$(openssl passwd -6 -stdin < "$password")"
[[ "$hash" == '$6$'* ]] || exit 4
install -d -m 0700 "$root/etc/135er-grow-central"
printf '%s\n' "$hash" > "$root/etc/135er-grow-central/operator-maint-password.hash"
chmod 0600 "$root/etc/135er-grow-central/operator-maint-password.hash"
unset hash
installer="$source_root/scripts/install-gc-maintenance-agent.sh"
[[ -f "$installer" ]] || { echo "Current maintenance installer missing" >&2; exit 4; }
grep -Fq 'MAINTENANCE_SUDO_VERIFIED=UID_0' "$installer" || {
  echo "Maintenance installer lacks actual root/sudo verification" >&2; exit 4;
}
install -o root -g root -m 0755 "$installer" "$root/opt/135er-grow-central/scripts/install-gc-maintenance-agent.sh"
[[ -f "$root/etc/systemd/system/grow-central-firstboot-maintenance.service" ]] || exit 4
grep -Fxq 'User=root' "$root/etc/systemd/system/grow-central-firstboot-maintenance.service" || exit 4
grep -Fxq 'NoNewPrivileges=no' "$root/etc/systemd/system/grow-central-firstboot-maintenance.service" || exit 4
# Preserve the base-source SHA and separately record the access-policy patch revision.
git -C "$source_root" rev-parse HEAD > "$root/opt/135er-grow-central/OPERATOR_ACCESS_PATCH_COMMIT"
printf '%s\n' 'FIXED_TEST_PASSWORD_SUDO_UID0_MESHCENTRAL' > "$root/opt/135er-grow-central/OPERATOR_ACCESS_POLICY"
install -o root -g root -m 0755 "$script" "$root/usr/local/sbin/gc-firstboot-maintenance-provision"
install -o root -g root -m 0755 "$script" "$root/opt/135er-grow-central/image-builder/firstboot/gc-firstboot-maintenance-provision.sh"
[[ -L "$root/etc/systemd/system/multi-user.target.wants/grow-central-firstboot-maintenance.service" ]] || exit 4
[[ -L "$root/etc/systemd/system/multi-user.target.wants/grow-central-mesh-agent.service" ]] || exit 4
[[ -L "$root/etc/systemd/system/multi-user.target.wants/ssh.service" ]] || exit 4
[[ -L "$root/etc/systemd/system/timers.target.wants/grow-central-remote-watchdog.timer" ]] || exit 4
sync
umount "$work/boot"; boot_on=0
umount "$work/root"; root_on=0
complete=1
echo "PRIVATE_FIXED_PASSWORD_IMAGE=$target"
echo "SHA256=$(sha256sum "$target" | cut -d' ' -f1)"
echo "MAINTENANCE_USER=gc-maint SUDO=full SSH_PASSWORD=enabled_after_first_boot"
echo "MESH_AGENT=bundled_and_autostart"
