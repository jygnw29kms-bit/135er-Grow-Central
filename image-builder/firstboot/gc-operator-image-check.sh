#!/usr/bin/env bash
# Read-only checklist for private Grow Central Raspberry Pi operator images.
# Does not show tokens, passwords, private keys, session identifiers or serials.
set -Eeuo pipefail
ROOT=/opt/135er-grow-central
FAILED=0
status() {
  local label="$1" result="$2"
  printf '%-36s %s\n' "$label" "$result"
}
unit_enabled() {
  local unit="$1"
  if systemctl is-enabled --quiet "$unit" 2>/dev/null; then
    status "$unit" ENABLED
  else
    status "$unit" NOT_ENABLED
    FAILED=1
  fi
}
unit_running() {
  local unit="$1"
  if systemctl is-active --quiet "$unit" 2>/dev/null; then
    status "$unit" RUNNING
  else
    status "$unit" NOT_RUNNING
    FAILED=1
  fi
}
status "Image release" "$(cat "$ROOT/BUILD" 2>/dev/null || echo UNKNOWN)"
status "Source commit" "$(head -c 40 "$ROOT/SOURCE_COMMIT" 2>/dev/null || echo UNKNOWN)"
status "Distribution policy" "OPERATOR_ONLY"
status "Runtime version" "$(cat "$ROOT/VERSION" 2>/dev/null || echo UNKNOWN)"
status "Machine type" "$(tr -d '\000' </proc/device-tree/model 2>/dev/null || echo UNKNOWN)"
for unit in ssh.service grow-central-firstboot-maintenance.service grow-central-remote-watchdog.timer grow-central-mesh-agent.service grow-central-homekit.service 135er-grow-central.service; do
  unit_enabled "$unit"
done
unit_running 135er-grow-central.service
unit_running grow-central-remote-watchdog.timer
unit_running ssh.service
if [[ -f "$ROOT/app/mars_legacy_telemetry.py" && -f "$ROOT/app/mars_hydro_ble.py" ]]; then
  status "Mars Hydro read-only decoder" PRESENT
else
  status "Mars Hydro read-only decoder" MISSING
  FAILED=1
fi
if [[ -f "$ROOT/app/provisioning/usb.py" ]]; then
  status "USB sensor onboarding" PRESENT
else
  status "USB sensor onboarding" CHECK_REQUIRED
fi
if [[ -x /opt/grow-central/mesh-agent/meshagent && -s /opt/grow-central/mesh-agent/meshagent.msh ]]; then
  if systemctl is-active --quiet grow-central-mesh-agent.service; then
    status "MeshCentral enrollment" RUNNING
  else
    status "MeshCentral enrollment" INSTALLED_NOT_RUNNING
    FAILED=1
  fi
else
  status "MeshCentral enrollment" NOT_PROVISIONED
fi
if id gc-maint >/dev/null 2>&1; then
  status "Key-only maintenance user" EXISTS
else
  status "Key-only maintenance user" NOT_PROVISIONED
fi
if command -v curl >/dev/null 2>&1 && curl -fsS --max-time 3 http://127.0.0.1:8080/api/health >/dev/null; then
  status "Grow Central HTTP health" OK
else
  status "Grow Central HTTP health" FAILED
  FAILED=1
fi
if [[ $FAILED -eq 0 ]]; then
  status "Base image smoke checks" PASS
else
  status "Base image smoke checks" FAIL
fi
echo "Live BLE, HomeKit pairing and sensor identity require real hardware tests."
exit "$FAILED"
