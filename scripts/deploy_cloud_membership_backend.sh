#!/usr/bin/env bash
# Install the tested room-membership module without exposing credentials.
# Usage: sudo bash scripts/deploy_cloud_membership_backend.sh /path/to/repo
set -Eeuo pipefail

repo="${1:?Pass checked-out repository root}"
source_file="$repo/cloud/v7/room_membership.py"
destination="/opt/135er-growcentral-cloud/cloud_room_membership.py"
service="135er-growcentral-cloud"
url="https://135ercloud.grow-central.de/api/v2/collaboration/my-rooms"
backup_root="/var/backups/grow-central"
test -f "$source_file"
test -f "$destination"
test "$EUID" -eq 0

python3 -m py_compile "$source_file"
backup="$(mktemp -d "$backup_root/room-membership-release.XXXXXXXX")"
chmod 700 "$backup"
cp -p "$destination" "$backup/cloud_room_membership.py"
rollback() {
  echo "Cloud room membership deployment failed; restoring previous module" >&2
  cp -p "$backup/cloud_room_membership.py" "$destination"
  systemctl restart "$service" || true
}
trap rollback ERR

install -o root -g root -m 644 "$source_file" "$destination"
cmp "$source_file" "$destination"
systemctl restart "$service"

# Static / may be served by nginx while the Python backend still returns 502.
# The protected endpoint MUST return 401 without a login; 502/503 are not ready.
ready=0
for attempt in $(seq 1 30); do
  if systemctl is-active --quiet "$service"; then
    code="$(curl -sS -o /dev/null -w '%{http_code}' --max-time 4 "$url" || true)"
    if [[ "$code" == "401" ]]; then ready=1; break; fi
  fi
  sleep 1
done
if [[ "$ready" != 1 ]]; then
  echo "Cloud membership API did not recover its authenticated boundary" >&2
  false
fi
cmp "$source_file" "$destination"
echo "Cloud room membership deployed; unauthed API rejects (401); previous version backed up at $backup"
trap - ERR
