#!/usr/bin/env bash
set -Eeuo pipefail

# This installer is intentionally part of the production deploy path: changes
# here trigger the Grow-Central Cloud/Plesk synchronization workflow.
SERVICE="${SERVICE:-135er-growcentral-cloud}"
PLATFORM_SERVICE="${PLATFORM_SERVICE:-135er-growcentral-cloud-platform}"
APP_USER="${APP_USER:-growcentral-cloud}"
APP_DIR="${APP_DIR:-/opt/${SERVICE}}"
DATA_DIR="${DATA_DIR:-/var/lib/${SERVICE}}"
CONF_DIR="${CONF_DIR:-/etc/${SERVICE}}"
ENV_FILE="${ENV_FILE:-${CONF_DIR}/cloud.env}"
SYSTEMD_FILE="/etc/systemd/system/${PLATFORM_SERVICE}.service"
GITHUB_RAW="${GITHUB_RAW:-https://raw.githubusercontent.com/jygnw29kms-bit/135er-Grow-Central/master}"
PLATFORM_SOURCE="${PLATFORM_SOURCE:-}"
ROUTER_SOURCE="${ROUTER_SOURCE:-}"
PLATFORM_PORT="${V7_PLATFORM_PORT:-18767}"

log(){ printf '\033[1;36m[GrowCentral Platform]\033[0m %s\n' "$*"; }
die(){ printf '\033[1;31m[FEHLER]\033[0m %s\n' "$*" >&2; exit 1; }

[[ $EUID -eq 0 ]] || die "Bitte als root ausführen."
[[ -r "$ENV_FILE" ]] || die "$ENV_FILE fehlt. Zuerst Cloud V7 installieren."
[[ -x "$APP_DIR/venv/bin/python" ]] || die "Cloud-Venv fehlt: $APP_DIR/venv"

install -d -m 0750 "$CONF_DIR"
if ! grep -q '^V7_PLATFORM_PORT=' "$ENV_FILE"; then
  printf 'V7_PLATFORM_PORT=%s\n' "$PLATFORM_PORT" >> "$ENV_FILE"
fi

set -a
# shellcheck disable=SC1090
. "$ENV_FILE"
set +a
PLATFORM_PORT="${V7_PLATFORM_PORT:-$PLATFORM_PORT}"

log "Installiere Platform-Status-App"
if [[ -n "$PLATFORM_SOURCE" ]]; then
  [[ -f "$PLATFORM_SOURCE" ]] || die "PLATFORM_SOURCE fehlt: $PLATFORM_SOURCE"
  install -m 0644 -o root -g root "$PLATFORM_SOURCE" "$APP_DIR/platform_status_v1.py"
else
  curl -fsSL "$GITHUB_RAW/cloud/v7/platform_status_app.py" -o "$APP_DIR/platform_status_v1.py"
fi
chown root:root "$APP_DIR/platform_status_v1.py"
chmod 0644 "$APP_DIR/platform_status_v1.py"

cat > "$SYSTEMD_FILE" <<EOF
[Unit]
Description=135er Grow Central Cloud Platform Status
After=${SERVICE}.service network-online.target
Requires=${SERVICE}.service

[Service]
Type=simple
User=${APP_USER}
Group=${APP_USER}
EnvironmentFile=${ENV_FILE}
WorkingDirectory=${APP_DIR}
ExecStart=${APP_DIR}/venv/bin/python -m uvicorn platform_status_v1:app --host 127.0.0.1 --port ${PLATFORM_PORT} --proxy-headers --forwarded-allow-ips=127.0.0.1
Restart=on-failure
RestartSec=3
NoNewPrivileges=true
PrivateTmp=true
PrivateDevices=true
ProtectSystem=strict
ProtectHome=true
ReadWritePaths=${DATA_DIR}
RestrictSUIDSGID=true
LockPersonality=true
UMask=0077

[Install]
WantedBy=multi-user.target
EOF

systemctl daemon-reload
systemctl enable "$PLATFORM_SERVICE" >/dev/null
systemctl restart "$PLATFORM_SERVICE"
sleep 1
systemctl is-active --quiet "$PLATFORM_SERVICE" || die "$PLATFORM_SERVICE startet nicht"
curl -fsS --connect-timeout 4 "http://127.0.0.1:${PLATFORM_PORT}/health" >/dev/null || die "Platform-Healthcheck fehlgeschlagen"

ROUTER="/usr/lib/${SERVICE}/configure-v7-routing.sh"
if [[ -n "$ROUTER_SOURCE" ]]; then
  [[ -f "$ROUTER_SOURCE" ]] || die "ROUTER_SOURCE fehlt: $ROUTER_SOURCE"
  install -m 0755 -o root -g root "$ROUTER_SOURCE" "$ROUTER"
else
  # Package/normal install path follows the selected repository channel.
  curl -fsSL "$GITHUB_RAW/scripts/configure-v7-routing.sh" -o "$ROUTER"
  chmod 0755 "$ROUTER"
fi
"$ROUTER"

log "Platform-Status aktiv auf 127.0.0.1:${PLATFORM_PORT}"
log "Öffentliche signierte API: /api/v7/platform/challenge und /api/v7/platform/report"
