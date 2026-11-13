#!/usr/bin/env bash
# Produce an OWNER-ONLY Grow Central Pi image with permanent SSH and MeshCentral
# enrollment. NEVER upload/share this output: it contains private agent config.
# Linux build machine with root, losetup, mount and a current universal .img.
set -Eeuo pipefail
umask 077

usage() {
  cat >&2 <<'HELP'
Usage: sudo bash scripts/build-private-pi-image.sh \
  --input /path/universal.img \
  --output /private/path/grow-central-owner.img \
  --public-key /private/path/owner.pub \
  --mesh-agent /private/path/meshagent \
  --mesh-config /private/path/meshagent.msh

Output is PRIVATE (contains an enrolled remote-access agent).
Pass the .img of a new Grow Central build that already includes the units.
Never upload it to public GitHub releases or CI artifacts.
HELP
  exit 2
}
[[ $EUID -eq 0 ]] || usage
input= output= pubkey= agent= config=
while (($#)); do
  case "$1" in
    --input) input="${2:-}"; shift 2 ;;
    --output) output="${2:-}"; shift 2 ;;
    --public-key) pubkey="${2:-}"; shift 2 ;;
    --mesh-agent) agent="${2:-}"; shift 2 ;;
    --mesh-config) config="${2:-}"; shift 2 ;;
    *) usage ;;
  esac
done
for v in input pubkey agent config; do
  [[ -n "${!v}" && -f "${!v}" && ! -L "${!v}" ]] || usage
done
[[ -n "$output" ]] || usage
[[ "$input" != "$output" ]] || { echo "Input and output must differ" >&2; exit 2; }
[[ ! -e "$output" ]] || { echo "Refusing to overwrite output" >&2; exit 2; }
[[ "$output" == *.img ]] || { echo "Uncompressed .img output required" >&2; exit 2; }
for cmd in losetup mount umount cp install ssh-keygen blkid sync sha256sum openssl sed; do
  command -v "$cmd" >/dev/null || { echo "Missing: $cmd" >&2; exit 2; }
done
[[ "$(stat -c %s "$pubkey")" -le 512 ]] || { echo "Public key file too large" >&2; exit 2; }
[[ "$(wc -l < "$pubkey")" -eq 1 ]] || { echo "Exactly one public SSH key required" >&2; exit 2; }
read -r keytype keydata _ < "$pubkey"
[[ "$keytype" == ssh-ed25519 && "$keydata" =~ ^[A-Za-z0-9+/]+={0,2}$ ]] || {
  echo "Expected an Ed25519 OpenSSH public key" >&2; exit 2;
}
ssh-keygen -lf "$pubkey" >/dev/null || { echo "Invalid public key" >&2; exit 2; }
[[ "$(stat -c %s "$agent")" -gt 10000 && "$(stat -c %s "$config")" -gt 16 ]] || {
  echo "Incomplete MeshCentral enrollment inputs" >&2; exit 2;
}
[[ "$(od -An -N4 -tx1 "$agent" | tr -d ' \n')" == 7f454c46 ]] || {
  echo "MeshCentral binary must be Linux ELF" >&2; exit 2;
}
# Hardware compatibility: image supports 64-bit Raspberry Pi OS ARM.
if command -v readelf >/dev/null; then
  readelf -h "$agent" | grep -q 'Machine:.*AArch64' || {
    echo "Expected AArch64 MeshCentral agent" >&2; exit 2;
  }
fi
input="$(realpath "$input")"
pubkey="$(realpath "$pubkey")"
agent="$(realpath "$agent")"
config="$(realpath "$config")"
output="$(realpath -m "$output")"
mkdir -p "$(dirname "$output")"
install -m 0600 "$input" "$output"
loop=""
tmp="$(mktemp -d /tmp/gc-private-image.XXXXXXXX)"
boot="$tmp/boot"
root="$tmp/root"
mkdir "$boot" "$root"
mounted_boot=0 mounted_root=0 completed=0
cleanup() {
  set +e
  [[ $mounted_boot -eq 1 ]] && umount "$boot"
  [[ $mounted_root -eq 1 ]] && umount "$root"
  [[ -n "$loop" ]] && losetup -d "$loop"
  rmdir "$boot" "$root" "$tmp" 2>/dev/null || true
  if [[ $completed -ne 1 ]]; then
    rm -f -- "$output"
    echo "Private image not completed; partial output deleted" >&2
  fi
}
trap cleanup EXIT
loop="$(losetup --find --show --partscan "$output")"
[[ -b "${loop}p1" && -b "${loop}p2" ]] || {
  echo "Expected Raspberry Pi partition layout" >&2; exit 3;
}
mount "${loop}p2" "$root"
mounted_root=1
mount "${loop}p1" "$boot"
mounted_boot=1
[[ -f "$root/opt/135er-grow-central/scripts/install-gc-maintenance-agent.sh" ]] || {
  echo "Image does not contain expected maintenance installer; use updated build" >&2; exit 4;
}
# Fail closed for old images: a current operator base must include its immutable source SHA.
source_file="$root/opt/135er-grow-central/SOURCE_COMMIT"
distribution_file="$root/opt/135er-grow-central/IMAGE_DISTRIBUTION"
[[ -f "$source_file" && -f "$distribution_file" ]] || {
  echo "This image predates current operator source tracking; rebuild from master" >&2; exit 4;
}
source_sha="$(tr -d '\r\n' < "$source_file")"
[[ "$source_sha" =~ ^[a-f0-9]{40}$ ]] || {
  echo "Invalid embedded source SHA" >&2; exit 4;
}
grep -Fxq 'OPERATOR_ONLY' "$distribution_file" || {
  echo "Expected operator-only image base" >&2; exit 4;
}
for unit in grow-central-firstboot-maintenance.service grow-central-mesh-agent.service; do
  [[ -f "$root/etc/systemd/system/$unit" ]] || {
    echo "Image missing $unit; use updated build" >&2; exit 4;
  }
done
# Operator media must be remotely maintainable from the FIRST boot.
for unit in ssh.service NetworkManager.service grow-central-firstboot-maintenance.service grow-central-mesh-agent.service grow-central-remote-watchdog.timer; do
  [[ -L "$root/etc/systemd/system/multi-user.target.wants/$unit" || -L "$root/etc/systemd/system/timers.target.wants/$unit" ]] || {
    echo "Mandatory first-boot service not enabled: $unit" >&2; exit 4;
  }
done
grep -Eq '^User=root
[[ ! -e "$boot/gc-maintenance.pub" ]] || {
  echo "Bootfs already has enrollment key" >&2; exit 4;
}
[[ ! -e "$root/opt/grow-central/mesh-agent/meshagent" ]] || {
  echo "Image already has MeshCentral enrollment" >&2; exit 4;
}
# Replace the image-building placeholders with per-image secrets, before
# first boot. Existing tokens must never be cloned across operator devices.
appenv="$root/opt/135er-grow-central/.env"
cloudenv="$root/opt/135er-grow-central/local/cloud_link/.env"
[[ -f "$appenv" && -f "$cloudenv" ]] || {
  echo "Expected runtime environment files not present" >&2; exit 4;
}
for item in "GC_API_TOKEN=test" "GC_LOCAL_API_TOKEN=test"; do
  grep -Fxq "$item" "$appenv" || {
    echo "Unrecognized runtime placeholder for ${item%%=*}; refusing to duplicate credentials" >&2; exit 4;
  }
done
grep -Fxq 'GC_LOCAL_API_TOKEN=test' "$cloudenv" || {
  echo "Unexpected cloud-link token placeholder" >&2; exit 4;
}
operator_token="$(openssl rand -hex 32)"
sed -i "s/^GC_API_TOKEN=test$/GC_API_TOKEN=$operator_token/" "$appenv"
sed -i "s/^GC_LOCAL_API_TOKEN=test$/GC_LOCAL_API_TOKEN=$operator_token/" "$appenv"
sed -i "s/^GC_LOCAL_API_TOKEN=test$/GC_LOCAL_API_TOKEN=$operator_token/" "$cloudenv"
unset operator_token
printf 'OPERATOR_PROVISIONED\n' > "$root/opt/135er-grow-central/IMAGE_DISTRIBUTION"
# Runtime services run as growcentral and need group-read of EnvironmentFile.
image_gid="$(awk -F: '$1 == "growcentral" {print $3; exit}' "$root/etc/group")"
[[ "$image_gid" =~ ^[0-9]+$ ]] || { echo "Grow Central group missing in image" >&2; exit 4; }
chown 0:"$image_gid" "$appenv" "$cloudenv"
chmod 0640 "$appenv" "$cloudenv"
# No static password is ever embedded in the operator image.
# One public key is applied by the firstboot systemd service.
cp -- "$pubkey" "$boot/gc-maintenance.pub"
# Device-bound config is private: never add this directory to Git or artifacts.
install -d -m 0700 "$root/opt/grow-central/mesh-agent"
install -m 0700 "$agent" "$root/opt/grow-central/mesh-agent/meshagent"
install -m 0600 "$config" "$root/opt/grow-central/mesh-agent/meshagent.msh"
[[ -L "$root/etc/systemd/system/multi-user.target.wants/grow-central-mesh-agent.service" ]] || {
  echo "Image has MeshCentral service installed but not enabled" >&2; exit 4;
}
sync
umount "$boot"; mounted_boot=0
umount "$root"; mounted_root=0
losetup -d "$loop"; loop=""
chmod 0600 "$output"
completed=1
echo "PRIVATE_OWNER_IMAGE_READY=$output"
echo "SOURCE_COMMIT=$source_sha"
echo "SHA256=$(sha256sum "$output" | awk '{print $1}')"
echo "SECURITY: keep this image private; revoke device enrollment if leaked."
echo "VALIDATION: real boot, SSH sudo and MeshCentral online check still required."
 "$root/etc/systemd/system/grow-central-firstboot-maintenance.service" || {
  echo "First-boot maintenance must run as root" >&2; exit 4;
}
grep -Eq '^NoNewPrivileges=no
[[ ! -e "$boot/gc-maintenance.pub" ]] || {
  echo "Bootfs already has enrollment key" >&2; exit 4;
}
[[ ! -e "$root/opt/grow-central/mesh-agent/meshagent" ]] || {
  echo "Image already has MeshCentral enrollment" >&2; exit 4;
}
# Replace the image-building placeholders with per-image secrets, before
# first boot. Existing tokens must never be cloned across operator devices.
appenv="$root/opt/135er-grow-central/.env"
cloudenv="$root/opt/135er-grow-central/local/cloud_link/.env"
[[ -f "$appenv" && -f "$cloudenv" ]] || {
  echo "Expected runtime environment files not present" >&2; exit 4;
}
for item in "GC_API_TOKEN=test" "GC_LOCAL_API_TOKEN=test"; do
  grep -Fxq "$item" "$appenv" || {
    echo "Unrecognized runtime placeholder for ${item%%=*}; refusing to duplicate credentials" >&2; exit 4;
  }
done
grep -Fxq 'GC_LOCAL_API_TOKEN=test' "$cloudenv" || {
  echo "Unexpected cloud-link token placeholder" >&2; exit 4;
}
operator_token="$(openssl rand -hex 32)"
sed -i "s/^GC_API_TOKEN=test$/GC_API_TOKEN=$operator_token/" "$appenv"
sed -i "s/^GC_LOCAL_API_TOKEN=test$/GC_LOCAL_API_TOKEN=$operator_token/" "$appenv"
sed -i "s/^GC_LOCAL_API_TOKEN=test$/GC_LOCAL_API_TOKEN=$operator_token/" "$cloudenv"
unset operator_token
printf 'OPERATOR_PROVISIONED\n' > "$root/opt/135er-grow-central/IMAGE_DISTRIBUTION"
# Runtime services run as growcentral and need group-read of EnvironmentFile.
image_gid="$(awk -F: '$1 == "growcentral" {print $3; exit}' "$root/etc/group")"
[[ "$image_gid" =~ ^[0-9]+$ ]] || { echo "Grow Central group missing in image" >&2; exit 4; }
chown 0:"$image_gid" "$appenv" "$cloudenv"
chmod 0640 "$appenv" "$cloudenv"
# No static password is ever embedded in the operator image.
# One public key is applied by the firstboot systemd service.
cp -- "$pubkey" "$boot/gc-maintenance.pub"
# Device-bound config is private: never add this directory to Git or artifacts.
install -d -m 0700 "$root/opt/grow-central/mesh-agent"
install -m 0700 "$agent" "$root/opt/grow-central/mesh-agent/meshagent"
install -m 0600 "$config" "$root/opt/grow-central/mesh-agent/meshagent.msh"
[[ -L "$root/etc/systemd/system/multi-user.target.wants/grow-central-mesh-agent.service" ]] || {
  echo "Image has MeshCentral service installed but not enabled" >&2; exit 4;
}
sync
umount "$boot"; mounted_boot=0
umount "$root"; mounted_root=0
losetup -d "$loop"; loop=""
chmod 0600 "$output"
completed=1
echo "PRIVATE_OWNER_IMAGE_READY=$output"
echo "SOURCE_COMMIT=$source_sha"
echo "SHA256=$(sha256sum "$output" | awk '{print $1}')"
echo "SECURITY: keep this image private; revoke device enrollment if leaked."
echo "VALIDATION: real boot, SSH sudo and MeshCentral online check still required."
 "$root/etc/systemd/system/grow-central-firstboot-maintenance.service" || {
  echo "First-boot maintenance would block sudo privileges" >&2; exit 4;
}
grep -Fq 'MAINTENANCE_SUDO_VERIFIED=UID_0' "$root/opt/135er-grow-central/scripts/install-gc-maintenance-agent.sh" || {
  echo "Base image lacks mandatory live sudo verification; rebuild from current master" >&2; exit 4;
}
grep -Fq 'gc-maintenance.pub' "$root/usr/local/sbin/gc-firstboot-maintenance-provision" || {
  echo "First-boot key provisioning unavailable" >&2; exit 4;
}
[[ ! -e "$boot/gc-maintenance.pub" ]] || {
  echo "Bootfs already has enrollment key" >&2; exit 4;
}
[[ ! -e "$root/opt/grow-central/mesh-agent/meshagent" ]] || {
  echo "Image already has MeshCentral enrollment" >&2; exit 4;
}
# Replace the image-building placeholders with per-image secrets, before
# first boot. Existing tokens must never be cloned across operator devices.
appenv="$root/opt/135er-grow-central/.env"
cloudenv="$root/opt/135er-grow-central/local/cloud_link/.env"
[[ -f "$appenv" && -f "$cloudenv" ]] || {
  echo "Expected runtime environment files not present" >&2; exit 4;
}
for item in "GC_API_TOKEN=test" "GC_LOCAL_API_TOKEN=test"; do
  grep -Fxq "$item" "$appenv" || {
    echo "Unrecognized runtime placeholder for ${item%%=*}; refusing to duplicate credentials" >&2; exit 4;
  }
done
grep -Fxq 'GC_LOCAL_API_TOKEN=test' "$cloudenv" || {
  echo "Unexpected cloud-link token placeholder" >&2; exit 4;
}
operator_token="$(openssl rand -hex 32)"
sed -i "s/^GC_API_TOKEN=test$/GC_API_TOKEN=$operator_token/" "$appenv"
sed -i "s/^GC_LOCAL_API_TOKEN=test$/GC_LOCAL_API_TOKEN=$operator_token/" "$appenv"
sed -i "s/^GC_LOCAL_API_TOKEN=test$/GC_LOCAL_API_TOKEN=$operator_token/" "$cloudenv"
unset operator_token
printf 'OPERATOR_PROVISIONED\n' > "$root/opt/135er-grow-central/IMAGE_DISTRIBUTION"
# Runtime services run as growcentral and need group-read of EnvironmentFile.
image_gid="$(awk -F: '$1 == "growcentral" {print $3; exit}' "$root/etc/group")"
[[ "$image_gid" =~ ^[0-9]+$ ]] || { echo "Grow Central group missing in image" >&2; exit 4; }
chown 0:"$image_gid" "$appenv" "$cloudenv"
chmod 0640 "$appenv" "$cloudenv"
# No static password is ever embedded in the operator image.
# One public key is applied by the firstboot systemd service.
cp -- "$pubkey" "$boot/gc-maintenance.pub"
# Device-bound config is private: never add this directory to Git or artifacts.
install -d -m 0700 "$root/opt/grow-central/mesh-agent"
install -m 0700 "$agent" "$root/opt/grow-central/mesh-agent/meshagent"
install -m 0600 "$config" "$root/opt/grow-central/mesh-agent/meshagent.msh"
[[ -L "$root/etc/systemd/system/multi-user.target.wants/grow-central-mesh-agent.service" ]] || {
  echo "Image has MeshCentral service installed but not enabled" >&2; exit 4;
}
sync
umount "$boot"; mounted_boot=0
umount "$root"; mounted_root=0
losetup -d "$loop"; loop=""
chmod 0600 "$output"
completed=1
echo "PRIVATE_OWNER_IMAGE_READY=$output"
echo "SOURCE_COMMIT=$source_sha"
echo "SHA256=$(sha256sum "$output" | awk '{print $1}')"
echo "SECURITY: keep this image private; revoke device enrollment if leaked."
echo "VALIDATION: real boot, SSH sudo and MeshCentral online check still required."
