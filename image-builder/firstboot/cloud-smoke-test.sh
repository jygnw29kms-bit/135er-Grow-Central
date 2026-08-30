#!/usr/bin/env bash
# Read-only compatibility probe for the optional Grow Central Cloud.
# Cloud availability must never decide whether a local-first image is valid.
set -u

CLOUD_ORIGIN="${GC_CLOUD_TEST_URL:-https://135ercloud.dezender.de}"
LOG_DIR="${GC_CLOUD_TEST_LOG_DIR:-/var/lib/135er-grow-central/support}"
LOG_FILE="${LOG_DIR}/cloud-smoke-latest.log"

install -d -m 0750 "$LOG_DIR" 2>/dev/null || true
: >"$LOG_FILE" 2>/dev/null || true
chmod 0640 "$LOG_FILE" 2>/dev/null || true
exec > >(tee -a "$LOG_FILE") 2>&1

printf '135er Grow Central optional cloud probe\nZeit UTC: %s\nCloud: %s\n' \
  "$(date -u '+%Y-%m-%dT%H:%M:%SZ')" "$CLOUD_ORIGIN"

host="${CLOUD_ORIGIN#https://}"
host="${host%%/*}"
if ! getent ahostsv4 "$host" >/dev/null 2>&1; then
  printf 'DEGRADED: Cloud-DNS nicht erreichbar; lokaler Betrieb bleibt gültig.\n'
  exit 0
fi

health=""
health_path=""
for path in /api/health /health; do
  if health="$(curl --fail --silent --show-error --proto '=https' --tlsv1.2 --connect-timeout 5 --max-time 10 "$CLOUD_ORIGIN$path" 2>/dev/null)"; then
    health_path="$path"
    break
  fi
done

if [ -z "$health_path" ]; then
  printf 'DEGRADED: Cloud-HTTPS/Health nicht kompatibel oder nicht erreichbar; lokaler Betrieb bleibt gültig.\n'
  exit 0
fi

if printf '%s' "$health" | jq -e '.ok == true' >/dev/null 2>&1; then
  printf 'OK: optionaler Cloud-Healthcheck über %s.\n' "$health_path"
else
  printf 'DEGRADED: Cloud antwortet, aber Health-Vertrag ist unbekannt; lokaler Betrieb bleibt gültig.\n'
fi

printf 'GESAMTSTATUS: LOCAL-FIRST OK\n'
exit 0
