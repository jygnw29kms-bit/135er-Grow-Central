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
loop=""
root_on=0
boot_on=0
complete=0
cleanup(){
  set +e
  [[ $boot_on -eq 1 ]] && umount "$work/boot"
  [[ $root_on -eq 1 ]] && umount "$work/root"
  [[ -n "$loop" ]] && losetup -d "$loop"
  rmdir "$work/boot" "$work/root" "$work" 2>/dev/null || :
  [[ $complete -eq 1 ]] || rm -f -- "$target"
}
trap cleanup EXIT
loop="$(losetup --find --show --partscan "$target")"
mount "$loop"p2 "$work/root"; root_on=1
mount "$loop"p1 "$work/boot"; boot_on=1
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
install -o root -g root -m 0755 "$script" "$root/usr/local/sbin/gc-firstboot-maintenance-provision"
install -o root -g root -m 0755 "$script" "$root/opt/135er-grow-central/image-builder/firstboot/gc-firstboot-maintenance-provision.sh"
[[ -L "$root/etc/systemd/system/multi-user.target.wants/grow-central-firstboot-maintenance.service" ]] || exit 4
sync
umount "$work/boot"; boot_on=0
umount "$work/root"; root_on=0
losetup -d "$loop"; loop=""
complete=1
echo "PRIVATE_FIXED_PASSWORD_IMAGE=$target"
echo "SHA256=$(sha256sum "$target" | cut -d' ' -f1)"
echo "MAINTENANCE_USER=gc-maint SUDO=full SSH_PASSWORD=enabled_after_first_boot"
echo "MESH_AGENT=bundled_and_autostart"
