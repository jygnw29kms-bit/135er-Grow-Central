#!/usr/bin/env bash
set -Eeuo pipefail
SERVICE="135er-growcentral-cloud"
APP_USER="growcentral-cloud"
APP_DIR="/opt/${SERVICE}"
ENV_FILE="/etc/${SERVICE}/cloud.env"

if [[ $EUID -ne 0 ]]; then echo "Bitte als root ausführen." >&2; exit 1; fi

systemctl stop "$SERVICE" 2>/dev/null || true

# Fix the venv created with an overly restrictive umask.
chown -R root:"$APP_USER" "$APP_DIR/venv"
chmod -R g+rX "$APP_DIR/venv"
chmod 0755 "$APP_DIR"
chmod 0644 "$APP_DIR/app.py"

# Remove root-only bytecode cache; the service can regenerate/use source safely.
rm -rf "$APP_DIR/__pycache__"

# Verify the service user can execute Python before restarting.
runuser -u "$APP_USER" -- "$APP_DIR/venv/bin/python" -c 'import sys; print(sys.version)'

systemctl daemon-reload
systemctl reset-failed "$SERVICE" || true
systemctl start "$SERVICE"
sleep 2

systemctl --no-pager --full status "$SERVICE" || true

PORT="$(grep '^APP_PORT=' "$ENV_FILE" | tail -1 | cut -d= -f2-)"
curl -fsS "http://127.0.0.1:${PORT}/health"
echo

echo "[OK] Laufzeitrechte repariert und Healthcheck erfolgreich."
