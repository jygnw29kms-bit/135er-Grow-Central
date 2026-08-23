#!/usr/bin/env bash
# Secrets-freier End-to-End-Smoke-Test des offiziellen GrowCentral-Cloud-Endpunkts.
set -Eeuo pipefail

CLOUD_ORIGIN="${GC_CLOUD_TEST_URL:-https://135ercloud.dezender.de}"
EXPECTED_HOST="${GC_CLOUD_TEST_HOST:-135ercloud.dezender.de}"
EXPECTED_IPV4="${GC_CLOUD_TEST_IPV4:-87.106.119.187}"
LOG_DIR="${GC_CLOUD_TEST_LOG_DIR:-/var/lib/135er-grow-central/support}"
LOG_FILE="${LOG_DIR}/cloud-smoke-latest.log"

install -d -m 0750 "$LOG_DIR"
: >"$LOG_FILE"
chmod 0640 "$LOG_FILE"
exec > >(tee -a "$LOG_FILE") 2>&1

ok() { printf 'OK   %s\n' "$*"; }
fail() { printf 'FAIL %s\n' "$*" >&2; exit 1; }

printf '135er GrowCentral Cloud Smoke Test\nZeit UTC: %s\nCloud: %s\n' \
  "$(date -u '+%Y-%m-%dT%H:%M:%SZ')" "$CLOUD_ORIGIN"

resolved="$(getent ahostsv4 "$EXPECTED_HOST" | awk 'NR==1{print $1}')"
[[ -n "$resolved" ]] || fail "DNS liefert keine IPv4-Adresse"
[[ "$resolved" == "$EXPECTED_IPV4" ]] || fail "DNS $resolved, erwartet $EXPECTED_IPV4"
ok "DNS $EXPECTED_HOST -> $resolved"

health="$(curl --fail --silent --show-error --proto '=https' --tlsv1.2 \
  --connect-timeout 8 --max-time 20 "$CLOUD_ORIGIN/health")"
jq -e '.ok == true and .service == "135er-growcentral-cloud"' <<<"$health" >/dev/null \
  || fail "Cloud-Healthcheck ungültig"
ok "HTTPS/TLS und /health"

discovery="$(curl --fail --silent --show-error --proto '=https' --tlsv1.2 \
  --connect-timeout 8 --max-time 20 "$CLOUD_ORIGIN/.well-known/growcentral-cloud")"
jq -e --arg origin "$CLOUD_ORIGIN" '
  .product == "135er-GrowCentral"
  and .official == true
  and .requires_https == true
  and .protocol_version >= 2
  and .public_url == $origin
  and (.device_websocket | startswith("wss://"))
  and (.remote_websocket | startswith("wss://"))
' <<<"$discovery" >/dev/null || fail "Cloud-Discovery ungültig"
ok "Discovery und WSS-Endpunkte"

# Keine Tokens, Registrierung, Telemetrie oder Remote-Schreibbefehle im Image-Test.
ok "Read-only; keine Secrets und keine Remote-Befehle verwendet"
printf 'GESAMTSTATUS: OK\n'
