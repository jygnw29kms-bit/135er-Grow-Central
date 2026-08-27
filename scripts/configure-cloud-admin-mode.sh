#!/usr/bin/env bash
set -Eeuo pipefail

CONF_DIR="${CONF_DIR:-/etc/135er-growcentral-cloud}"
MODE_FILE="${MODE_FILE:-${CONF_DIR}/admin-mode}"
ENV_FILE="${ENV_FILE:-${CONF_DIR}/cloud.env}"
MODE=""
NONINTERACTIVE=0

usage(){
  cat <<'EOF'
135er Grow Central Cloud – Admin-Modus

Aufruf:
  configure-cloud-admin-mode.sh [--mode standalone|plesk|both] [--noninteractive]

Ohne --mode wird bei einer interaktiven Erstinstallation gefragt. Bei APT-Upgrades
wird eine vorhandene Auswahl unverändert übernommen.
EOF
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --mode) MODE="${2:-}"; shift 2;;
    --noninteractive) NONINTERACTIVE=1; shift;;
    -h|--help) usage; exit 0;;
    *) echo "Unbekannte Option: $1" >&2; usage; exit 2;;
  esac
done

[[ $EUID -eq 0 ]] || { echo "Bitte als root ausführen." >&2; exit 1; }

PLESK=0
if command -v plesk >/dev/null 2>&1 || [[ -x /usr/local/psa/bin/plesk ]]; then
  PLESK=1
fi

install -d -m 0750 "$CONF_DIR"

# Existing installations keep their selected mode across apt upgrade.
if [[ -z "$MODE" && -s "$MODE_FILE" ]]; then
  MODE="$(tr -d '[:space:]' < "$MODE_FILE")"
fi

if [[ -z "$MODE" ]]; then
  if [[ "$PLESK" -eq 1 && "$NONINTERACTIVE" -eq 0 && -t 0 ]]; then
    echo "Plesk wurde auf diesem Server erkannt."
    echo "  [1] Plesk-Integration"
    echo "  [2] Grow Central Standalone-Webinterface"
    echo "  [3] Beides"
    read -r -p "Auswahl [1-3]: " choice
    case "$choice" in
      1) MODE="plesk";;
      3) MODE="both";;
      *) MODE="standalone";;
    esac
  else
    MODE="standalone"
  fi
fi

case "$MODE" in
  standalone|plesk|both) ;;
  *) echo "Ungültiger Admin-Modus: $MODE" >&2; exit 2;;
esac

if [[ "$MODE" == "plesk" && "$PLESK" -ne 1 ]]; then
  echo "Plesk-Modus angefordert, aber Plesk wurde nicht gefunden." >&2
  exit 3
fi

printf '%s\n' "$MODE" > "$MODE_FILE"
chmod 0640 "$MODE_FILE"

# Preserve all existing secrets/settings. Only append missing admin values.
touch "$ENV_FILE"
chmod 0640 "$ENV_FILE"
if ! grep -q '^CLOUD_ADMIN_MODE=' "$ENV_FILE"; then
  printf 'CLOUD_ADMIN_MODE=%s\n' "$MODE" >> "$ENV_FILE"
else
  sed -i "s/^CLOUD_ADMIN_MODE=.*/CLOUD_ADMIN_MODE=${MODE}/" "$ENV_FILE"
fi
if ! grep -q '^CLOUD_ADMIN_TOKEN=' "$ENV_FILE"; then
  printf 'CLOUD_ADMIN_TOKEN=%s\n' "$(openssl rand -hex 32)" >> "$ENV_FILE"
fi
if ! grep -q '^CLOUD_MAX_DEVICES=' "$ENV_FILE"; then printf 'CLOUD_MAX_DEVICES=1000\n' >> "$ENV_FILE"; fi
if ! grep -q '^CLOUD_HEARTBEAT_SECONDS=' "$ENV_FILE"; then printf 'CLOUD_HEARTBEAT_SECONDS=30\n' >> "$ENV_FILE"; fi
if ! grep -q '^CLOUD_OFFLINE_AFTER_SECONDS=' "$ENV_FILE"; then printf 'CLOUD_OFFLINE_AFTER_SECONDS=120\n' >> "$ENV_FILE"; fi

echo "Grow Central Admin-Modus: $MODE"
echo "Plesk erkannt: $([[ "$PLESK" -eq 1 ]] && echo ja || echo nein)"
echo "Konfiguration: $MODE_FILE"
