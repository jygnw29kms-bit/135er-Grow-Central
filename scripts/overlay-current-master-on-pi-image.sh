#!/usr/bin/env bash
# Offline conversion of verified Build 508 into current-master operator base.
# No shared credentials or secrets are committed to the source repository.
set -Eeuo pipefail
umask 077
[[ $EUID -eq 0 && $# -eq 3 ]] || { echo "Usage: sudo $0 verified-base.img current-source-dir new-overlay.img" >&2; exit 2; }
base="$(realpath "$1")"; source="$(realpath "$2")"; out="$(realpath -m "$3")"
[[ -f "$base" && -d "$source/.git" && ! -e "$out" && "$out" == *.img ]] || exit 2
commit="$(git -C "$source" rev-parse HEAD)"
[[ "$commit" =~ ^[a-f0-9]{40}$ ]] || exit 2
cp --reflink=auto --sparse=always "$base" "$out"
chmod 0600 "$out"
tmp="$(mktemp -d /tmp/gc-overlay.XXXXXXXX)"
root="$tmp/root"; boot="$tmp/boot"; mkdir "$root" "$boot"
loop=""; root_on=0; boot_on=0; success=0
cleanup(){
  set +e
  [[ $boot_on -eq 1 ]] && umount "$boot"
  [[ $root_on -eq 1 ]] && umount "$root"
  [[ -n "$loop" ]] && losetup -d "$loop"
  rmdir "$root" "$boot" "$tmp" 2>/dev/null || :
  [[ $success -eq 1 ]] || rm -f -- "$out"
}
trap cleanup EXIT
loop="$(losetup --find --show --partscan "$out")"
mount "$loop"p2 "$root"; root_on=1
mount "$loop"p1 "$boot"; boot_on=1
app="$root/opt/135er-grow-central"
[[ -d "$app/.venv" && -f "$app/BUILD" && -f "$app/app/entrypoint.py" ]] || exit 3
[[ ! -f "$root/var/lib/135er-grow-central/.headless-firstboot-ready" ]] || exit 3

rsync -a --exclude='.git/' --exclude='.github/' --exclude='.venv/' \
  --exclude='.env' --exclude='data/' --exclude='local/cloud_link/.env' \
  --exclude='BUILD' --exclude='SOURCE_COMMIT' --exclude='IMAGE_DISTRIBUTION' \
  --exclude='*.img' --exclude='*.img.xz' \
  "$source/" "$app/"
printf '%s\n' "$commit" > "$app/SOURCE_COMMIT"
printf '%s\n' 'OPERATOR_ONLY' > "$app/IMAGE_DISTRIBUTION"
printf '%s\n' "operator-$(git -C "$source" rev-parse --short=12 HEAD)-base508" > "$app/BUILD"

for item in gc-firstboot-maintenance-provision gc-remote-watchdog gc-operator-image-check; do
  case "$item" in
    gc-firstboot-maintenance-provision) src="gc-firstboot-maintenance-provision.sh";;
    gc-remote-watchdog) src="gc-remote-watchdog.sh";;
    gc-operator-image-check) src="gc-operator-image-check.sh";;
  esac
  install -o root -g root -m 0755 "$source/image-builder/firstboot/$src" "$root/usr/local/sbin/$item"
done
install -o root -g root -m 0755 "$source/image-builder/firstboot/apply_setup.py" "$root/usr/local/sbin/grow-central-apply-setup.py"
for unit in grow-central-firstboot-maintenance.service grow-central-remote-watchdog.service grow-central-remote-watchdog.timer grow-central-mesh-agent.service; do
  install -o root -g root -m 0644 "$source/systemd/$unit" "$root/etc/systemd/system/$unit"
done
install -D -o root -g root -m 0644 "$source/systemd/grow-central-ssh-hostkeys.conf" "$root/etc/systemd/system/ssh.service.d/20-grow-central-hostkeys.conf"

python3 - "$root" <<'PY'
from pathlib import Path
import sys
root=Path(sys.argv[1])
p=root/"usr/local/sbin/grow-central-headless-firstboot.sh"
s=p.read_text()
old='''if [[ -e /etc/135er-grow-central/test-maintenance-enabled ]]; then
  # Pristine images have no baked-in SSH host private keys.
  # Each Pi regenerates its own host keys before exposing SSH.
  ssh-keygen -A >/dev/null
  systemctl enable --now ssh.service >/dev/null 2>&1 || systemctl start ssh.service
else
  for unit in ssh.socket ssh.service sshd.service; do systemctl disable --now "$unit" >/dev/null 2>&1 || true; done
fi'''
new='''# Always keep SSH transport running; access requires individual public key.
ssh-keygen -A >/dev/null
/usr/sbin/sshd -t
systemctl enable --now ssh.service >/dev/null 2>&1 || systemctl start ssh.service'''
if s.count(old)!=1: raise SystemExit("Unknown firstboot script; stopped")
p.write_text(s.replace(old,new))
p=root/"usr/local/sbin/grow-central-firstboot-firewall.sh"
s=p.read_text()
old='''if [[ -e /etc/135er-grow-central/test-maintenance-enabled ]]; then
  # Test-image maintenance SSH is LAN-only and key-only.
  ufw allow from 10.0.0.0/8 to any port 22 proto tcp
  ufw allow from 172.16.0.0/12 to any port 22 proto tcp
  ufw allow from 192.168.0.0/16 to any port 22 proto tcp
fi'''
new='''# Only private LAN clients can reach key-only maintenance SSH.
ufw allow from 10.0.0.0/8 to any port 22 proto tcp
ufw allow from 172.16.0.0/12 to any port 22 proto tcp
ufw allow from 192.168.0.0/16 to any port 22 proto tcp'''
if s.count(old)!=1: raise SystemExit("Unknown firewall script; stopped")
p.write_text(s.replace(old,new))
# Revoke the legacy gcmaint identity without affecting any other user.
p=root/"etc/shadow"
lines=[]
for line in p.read_text().splitlines():
  parts=line.split(":")
  if parts[0]=="gcmaint": parts[1]="!"
  lines.append(":".join(parts))
p.write_text("\n".join(lines)+"\n")
p=root/"etc/passwd"
lines=[]
for line in p.read_text().splitlines():
  parts=line.split(":")
  if parts[0]=="gcmaint": parts[-1]="/usr/sbin/nologin"
  lines.append(":".join(parts))
p.write_text("\n".join(lines)+"\n")
PY
rm -f "$root/etc/135er-grow-central/test-maintenance-enabled" \
 "$root/etc/ssh/sshd_config.d/98-grow-central-test-maintenance.conf" \
 "$root/etc/sudoers.d/growcentral-maint" \
 "$root/home/gcmaint/.ssh/authorized_keys" "$boot/gc-maintenance.pub"
find "$root/etc/ssh" -maxdepth 1 -name 'ssh_host_*_key*' -type f -delete
: > "$root/etc/machine-id"
rm -f "$root/var/lib/dbus/machine-id"

# Offline enable by writing only target-image systemd symlinks.
# Do NOT call systemctl --root enable ssh: Debian's SysV compatibility
# calls ARM64 update-rc.d via chroot, which cannot execute on x86 builders.
[[ -f "$root/usr/lib/systemd/system/ssh.service" || -f "$root/lib/systemd/system/ssh.service" ]] || {
  echo "SSH systemd unit missing from Raspberry Pi base" >&2; exit 4;
}
install -d "$root/etc/systemd/system/multi-user.target.wants" "$root/etc/systemd/system/timers.target.wants"
ln -sfn /usr/lib/systemd/system/ssh.service "$root/etc/systemd/system/multi-user.target.wants/ssh.service"
for unit in grow-central-firstboot-maintenance.service grow-central-mesh-agent.service; do
  ln -sfn "/etc/systemd/system/$unit" "$root/etc/systemd/system/multi-user.target.wants/$unit"
done
ln -sfn /etc/systemd/system/grow-central-remote-watchdog.timer "$root/etc/systemd/system/timers.target.wants/grow-central-remote-watchdog.timer"
rm -f "$root/etc/systemd/system/sockets.target.wants/ssh.socket" "$root/etc/systemd/system/multi-user.target.wants/ssh.socket"
test -s "$app/app/mars_legacy_telemetry.py"
test -s "$app/app/mars_hydro_ble.py"
test -x "$root/usr/local/sbin/gc-operator-image-check"
test ! -e "$root/home/gcmaint/.ssh/authorized_keys"
test "$(cat "$app/SOURCE_COMMIT")" = "$commit"
sync
umount "$boot"; boot_on=0
umount "$root"; root_on=0
losetup -d "$loop"; loop=""
success=1
echo "OVERLAY_READY=$out"
echo "SOURCE_COMMIT=$commit"
echo "SHA256=$(sha256sum "$out" | cut -d ' ' -f1)"
