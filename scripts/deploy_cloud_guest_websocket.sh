#!/usr/bin/env bash
# Safe, additive Cloud guest-WebSocket rollout with one-command rollback.
# Only the Plesk Grow-Central Cloud v4 service is affected.
set -Eeuo pipefail
umask 077

repo="${1:?Provide freshly checked out Grow-Central repository path}"
root=/opt/135er-growcentral-cloud
backup=/var/backups/grow-central/cloud-guest-websocket-20261116
src="$repo/cloud/v7"
test -s "$repo/scripts/patch_cloud_guest_websocket.py"
test -s "$src/room_membership.py"
test -s "$src/guest_remote_acl.py"
test -s "$src/guest_websocket.py"
test -x "$root/venv/bin/python"
test -s "$root/app.py"
test ! -e "$root/cloud_guest_remote.py"
test ! -e "$root/guest_remote_acl.py"
! grep -q 'GROW_CENTRAL_BETA_GUEST_WEBSOCKET_V1' "$root/app.py"

work=$(mktemp -d /tmp/gc-guest-rollout.XXXXXXXX)
trap 'rm -rf "$work"' EXIT
python3 "$repo/scripts/patch_cloud_guest_websocket.py" \
  --source "$root/app.py" --output "$work/patched-app.py"
"$root/venv/bin/python" -m py_compile \
  "$work/patched-app.py" "$src/room_membership.py" \
  "$src/guest_remote_acl.py" "$src/guest_websocket.py"

install -d -m 700 "$backup"
cp -p "$root/app.py" "$backup/app.py"
cp -p "$root/cloud_room_membership.py" "$backup/cloud_room_membership.py"

rollback() {
  trap - ERR
  cp -p "$backup/app.py" "$root/app.py"
  cp -p "$backup/cloud_room_membership.py" "$root/cloud_room_membership.py"
  rm -f "$root/cloud_guest_remote.py" "$root/guest_remote_acl.py"
  systemctl restart 135er-growcentral-cloud || true
  echo 'CLOUD_GUEST_ROLLBACK_EXECUTED'
}
trap rollback ERR

install -m 644 "$src/room_membership.py" "$root/cloud_room_membership.py"
install -m 644 "$src/guest_remote_acl.py" "$root/guest_remote_acl.py"
install -m 644 "$src/guest_websocket.py" "$root/cloud_guest_remote.py"
PYTHONPATH="$root" "$root/venv/bin/python" - <<'PY'
import cloud_guest_remote
import cloud_room_membership
import guest_remote_acl
assert cloud_guest_remote.CloudGuestRemote
print('CLOUD_RUNTIME_IMPORT_PASS')
PY
install -m 644 "$work/patched-app.py" "$root/app.py"
systemctl restart 135er-growcentral-cloud

healthy=0
for number in 1 2 3 4 5 6 7 8 9 10 11 12 13 14 15; do
  if curl --fail --silent --show-error --max-time 2 \
       http://127.0.0.1:18765/health >"$work/health" 2>/dev/null; then
    healthy=1
    break
  fi
  sleep 1
done
if [ "$healthy" != 1 ]; then
  echo 'Cloud did not recover after guest WebSocket integration' >&2
  false
fi

# Test explicit rejection of an unauthenticated guest on the live local port.
"$root/venv/bin/python" - <<'PY'
import json
from websockets.sync.client import connect
from websockets.exceptions import ConnectionClosed
try:
    with connect('ws://127.0.0.1:18765/api/v2/collaboration/remote/connect',
                 open_timeout=5, close_timeout=1) as socket:
        socket.send(json.dumps({'type':'auth','access_token':'invalid',
                                'device_id':'device-invalid','room_id':'room_invalid'}))
        socket.recv(timeout=5)
    raise RuntimeError('Guest endpoint did not deny invalid token')
except ConnectionClosed as error:
    code = error.rcvd.code if error.rcvd else None
    if code not in (4401, 4403):
        raise RuntimeError('Unexpected guest auth closure: '+str(code))
    print('GUEST_AUTH_DENIAL_PASS', code)
PY

cmp "$src/room_membership.py" "$root/cloud_room_membership.py"
cmp "$src/guest_remote_acl.py" "$root/guest_remote_acl.py"
cmp "$src/guest_websocket.py" "$root/cloud_guest_remote.py"
systemctl is-active --quiet 135er-growcentral-cloud
systemctl is-active --quiet nginx
trap - ERR
echo 'CLOUD_GUEST_WEBSOCKET_DEPLOYED'
echo "SOURCE_REVISION=$(git -C "$repo" rev-parse --short HEAD)"
echo "HTTP_HEALTH=$(curl --silent --output /dev/null --write-out '%{http_code}' \
  --max-time 5 https://135ercloud.grow-central.de/)"
