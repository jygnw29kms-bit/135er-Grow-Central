#!/usr/bin/env bash
# Grow Central Pi: inspect and (optionally) install verified Mars Legacy backend.
# Safe by default: without --apply, only stages files and reports differences.
set -Eeuo pipefail
umask 077
ROOT=/opt/135er-grow-central
SERVICE=135er-grow-central.service
BASE_URL=https://raw.githubusercontent.com/jygnw29kms-bit/135er-Grow-Central
REF="${GC_DEPLOY_REF:-master}"
MODE=inspect
if [[ ${1:-} == --apply ]]; then MODE=apply; shift; fi
if (($#)); then echo "Usage: $0 [--apply]" >&2; exit 2; fi
if [[ ! "$REF" =~ ^[A-Za-z0-9._/-]+$ || "$REF" == *..* ]]; then
  echo "Invalid GC_DEPLOY_REF" >&2; exit 2
fi
if [[ "$MODE" == apply && "$EUID" -ne 0 ]]; then
  echo "Apply requires root (sudo)" >&2; exit 2
fi
if [[ ! -d "$ROOT/app" || ! -f "$ROOT/app/main.py" ]]; then
  echo "Expected existing Grow Central application not found at $ROOT" >&2; exit 2
fi
for command in curl python3 sha256sum diff; do
  command -v "$command" >/dev/null || { echo "Missing $command" >&2; exit 2; }
done
STAGE="$(mktemp -d /tmp/gc-mars-legacy.XXXXXX)"
trap 'rm -rf "$STAGE"' EXIT
files=(app/mars_hydro_ble.py app/mars_legacy_telemetry.py)
for name in "${files[@]}"; do
  mkdir -p "$STAGE/$(dirname "$name")"
  curl -fLsS --connect-timeout 8 --max-time 25 "$BASE_URL/$REF/$name" -o "$STAGE/$name"
  [[ -s "$STAGE/$name" ]] || { echo "Download empty: $name" >&2; exit 3; }
done
python3 -m py_compile "${files[@]/#/$STAGE/}"
echo "MODE=$MODE"
echo "REF=$REF"
for name in "${files[@]}"; do
  local_file="$ROOT/$name"
  if [[ -f "$local_file" ]]; then
    echo "LOCAL_SHA256 $(sha256sum "$local_file")"
    echo "CANDIDATE_SHA256 $(sha256sum "$STAGE/$name")"
    diff -u "$local_file" "$STAGE/$name" | head -n 100 || true
  else
    echo "LOCAL_MISSING $name"
  fi
done
if [[ "$MODE" == inspect ]]; then
  echo "DRY_RUN_COMPLETE: no application files modified, no services restarted"
  exit 0
fi
systemctl cat "$SERVICE" >/dev/null || { echo "Service not found: $SERVICE" >&2; exit 4; }
backup="$ROOT/data/maintenance-backups/mars-legacy-$(date -u +%Y%m%dT%H%M%SZ)"
install -d -m 0700 "$backup"
# Snapshot only relevant files. Mark missing ones to ensure rollback removes them.
for name in "${files[@]}"; do
  mkdir -p "$backup/$(dirname "$name")"
  if [[ -f "$ROOT/$name" ]]; then
    cp -a "$ROOT/$name" "$backup/$name"
  else
    : > "$backup/$name.ABSENT"
  fi
done
rollback() {
  echo "ROLLBACK from $backup" >&2
  for name in "${files[@]}"; do
    if [[ -f "$backup/$name.ABSENT" ]]; then
      rm -f "$ROOT/$name"
    else
      cp -a "$backup/$name" "$ROOT/$name"
    fi
  done
  systemctl restart "$SERVICE" || true
}
trap 'rollback; exit 6' ERR
for name in "${files[@]}"; do
  install -m 0644 "$STAGE/$name" "$ROOT/$name"
done
python3 -m py_compile "${files[@]/#/$ROOT/}"
systemctl restart "$SERVICE"
health_ok=0
for attempt in {1..15}; do
  if curl -fLsS --max-time 3 http://127.0.0.1:8080/api/health | grep -q '"ok":true'; then
    health_ok=1
    break
  fi
  sleep 1
done
if [[ "$health_ok" -ne 1 ]]; then
  echo "Health check failed" >&2
  false
fi
trap - ERR
echo "DEPLOYED_MARS_LEGACY_BACKEND"
echo "BACKUP=$backup"
echo "STATUS=health_ok; BLE live hardware verification still pending"
