#!/bin/bash
set -euo pipefail

APP=/opt/135er-grow-central
STAGE=/home/GrowCentral
STATE=/var/lib/135er-grow-central
COMMIT=d41a7aed29c53cdf6fd75fefe7007035f4bd5d41
STAMP=$(date -u +%Y%m%dT%H%M%SZ)
BACKUP="$STATE/manual-backups/${STAMP}-${COMMIT:0:12}"
CORE=135er-grow-central.service
CLOUD=135er-grow-central-cloud-link.service
HOMEKIT=grow-central-homekit.service

mkdir -p "$BACKUP/files"
: > "$BACKUP/created.list"
cp -a "$STAGE/MANIFEST.txt" "$STAGE/DELETE.txt" "$STAGE/runtime.tar.gz.sha256" "$BACKUP/"

rollback() {
  rc=$?
  trap - ERR INT TERM
  set +e
  echo "ROLLBACK rc=$rc"
  systemctl stop "$HOMEKIT" "$CLOUD" "$CORE"
  if [ -d "$BACKUP/files" ]; then
    cp -a "$BACKUP/files/." "$APP/"
  fi
  while IFS= read -r rel; do
    [ -n "$rel" ] && rm -f "$APP/$rel"
  done < "$BACKUP/created.list"
  systemctl start "$CORE"
  sleep 2
  systemctl start "$CLOUD" "$HOMEKIT"
  exit "$rc"
}
trap rollback ERR INT TERM

cd "$STAGE"
sha256sum -c runtime.tar.gz.sha256

while IFS= read -r rel; do
  case "$rel" in
    base=*|commit=*|'') continue ;;
  esac
  if [ -e "$APP/$rel" ]; then
    mkdir -p "$BACKUP/files/$(dirname "$rel")"
    cp -a "$APP/$rel" "$BACKUP/files/$rel"
  else
    echo "$rel" >> "$BACKUP/created.list"
  fi
done < "$STAGE/MANIFEST.txt"

while IFS= read -r rel; do
  [ -z "$rel" ] && continue
  if [ -e "$APP/$rel" ] && [ ! -e "$BACKUP/files/$rel" ]; then
    mkdir -p "$BACKUP/files/$(dirname "$rel")"
    cp -a "$APP/$rel" "$BACKUP/files/$rel"
  fi
done < "$STAGE/DELETE.txt"

systemctl stop "$HOMEKIT" "$CLOUD" "$CORE"

"$APP/.venv/bin/pip" install --disable-pip-version-check 'cryptography>=45,<47'

tar -xzf "$STAGE/runtime.tar.gz" -C "$APP"
while IFS= read -r rel; do
  [ -n "$rel" ] && rm -f "$APP/$rel"
done < "$STAGE/DELETE.txt"

while IFS= read -r rel; do
  case "$rel" in
    base=*|commit=*|'') continue ;;
  esac
  chown growcentral:growcentral "$APP/$rel"
  chmod 0644 "$APP/$rel"
done < "$STAGE/MANIFEST.txt"

PYTHONPYCACHEPREFIX=/tmp/gc-live-pyc "$APP/.venv/bin/python" -m compileall -q "$APP/app" "$APP/local/cloud_link" "$APP/shared"
rm -rf /tmp/gc-live-pyc

install -o root -g root -m 0755 "$STAGE/growcentral-maint.full" /usr/local/sbin/growcentral-maint
cat >/etc/sudoers.d/growcentral-maint <<'EOF'
GrowCentral ALL=(root) NOPASSWD: /usr/local/sbin/growcentral-maint status
GrowCentral ALL=(root) NOPASSWD: /usr/local/sbin/growcentral-maint restart-core
GrowCentral ALL=(root) NOPASSWD: /usr/local/sbin/growcentral-maint restart-cloud
GrowCentral ALL=(root) NOPASSWD: /usr/local/sbin/growcentral-maint restart-homekit
GrowCentral ALL=(root) NOPASSWD: /usr/local/sbin/growcentral-maint restart-all
GrowCentral ALL=(root) NOPASSWD: /usr/local/sbin/growcentral-maint apply-staged
EOF
chmod 0440 /etc/sudoers.d/growcentral-maint
visudo -cf /etc/sudoers.d/growcentral-maint

systemctl start "$CORE"
sleep 3
curl --fail --silent --show-error --max-time 12 http://127.0.0.1:8080/api/health | jq -e '.ok == true and .service == "135er-Grow Central Local"' >/dev/null
systemctl start "$CLOUD" "$HOMEKIT"
systemctl is-active --quiet "$CLOUD"
systemctl is-active --quiet "$HOMEKIT"
printf '%s\n' "$COMMIT" > "$APP/.live-git-sha"
chown root:growcentral "$APP/.live-git-sha"
chmod 0644 "$APP/.live-git-sha"

trap - ERR INT TERM
echo "APPLIED=$COMMIT"
echo "BACKUP=$BACKUP"
/usr/local/sbin/growcentral-maint status
