#!/usr/bin/env bash
set -Eeuo pipefail

SERVICE="${SERVICE:-135er-growcentral-cloud}"
CONF_DIR="${CONF_DIR:-/etc/${SERVICE}}"
ENV_FILE="${ENV_FILE:-${CONF_DIR}/cloud.env}"
MODE_FILE="${MODE_FILE:-${CONF_DIR}/admin-mode}"
[[ $EUID -eq 0 ]] || { echo "Bitte als root ausführen." >&2; exit 1; }
[[ -r "$ENV_FILE" ]] || { echo "$ENV_FILE fehlt." >&2; exit 1; }

set -a
# shellcheck disable=SC1090
. "$ENV_FILE"
set +a
MODE="$(cat "$MODE_FILE" 2>/dev/null || printf '%s' "${CLOUD_ADMIN_MODE:-standalone}")"
CORE_PORT="${APP_PORT:-18765}"
ADMIN_PORT="${V7_ADMIN_PORT:?V7_ADMIN_PORT fehlt}"
HOST="${PUBLIC_URL#https://}"; HOST="${HOST#http://}"; HOST="${HOST%%/*}"

write_locations(){
  cat <<EOF
# BEGIN 135ER-GROWCENTRAL-V7
location ^~ /api/v7/device/ {
    proxy_pass http://127.0.0.1:${ADMIN_PORT};
    proxy_http_version 1.1;
    proxy_set_header Host \$host;
    proxy_set_header X-Real-IP \$remote_addr;
    proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
    proxy_set_header X-Forwarded-Proto \$scheme;
    proxy_buffering off;
}
location ^~ /api/admin/ {
    proxy_pass http://127.0.0.1:${ADMIN_PORT};
    proxy_http_version 1.1;
    proxy_set_header Host \$host;
    proxy_set_header X-Real-IP \$remote_addr;
    proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
    proxy_set_header X-Forwarded-Proto \$scheme;
    proxy_buffering off;
}
location = /admin {
    proxy_pass http://127.0.0.1:${ADMIN_PORT}/admin;
    proxy_set_header Host \$host;
    proxy_set_header X-Forwarded-Proto \$scheme;
}
location = /v7/health {
    proxy_pass http://127.0.0.1:${ADMIN_PORT}/health;
}
# END 135ER-GROWCENTRAL-V7
EOF
}

strip_managed_block(){
  python3 - "$1" <<'PY'
from pathlib import Path
import sys,re
p=Path(sys.argv[1])
s=p.read_text() if p.exists() else ""
s=re.sub(r"(?ms)^# BEGIN 135ER-GROWCENTRAL-V7\n.*?^# END 135ER-GROWCENTRAL-V7\n?", "", s)
p.write_text(s)
PY
}

configure_standalone(){
  command -v nginx >/dev/null 2>&1 || { echo "nginx fehlt." >&2; exit 2; }
  local conf="/etc/nginx/sites-available/135er-growcentral-cloud.conf"
  cat > "$conf" <<EOF
server {
    listen 80;
    server_name ${HOST};
    client_max_body_size 16m;
    proxy_buffering off;
$(write_locations)
    location / {
        proxy_pass http://127.0.0.1:${CORE_PORT};
        proxy_http_version 1.1;
        proxy_set_header Upgrade \$http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
    }
}
EOF
  ln -sfn "$conf" /etc/nginx/sites-enabled/135er-growcentral-cloud.conf
  nginx -t
  systemctl reload nginx
  echo "Standalone V7 routing aktiv."
}

configure_plesk(){
  command -v plesk >/dev/null 2>&1 || { echo "Plesk-Modus gewählt, Plesk fehlt." >&2; exit 3; }
  local dir="/var/www/vhosts/system/${HOST}/conf" file backup tmp
  file="$dir/vhost_nginx.conf"
  [[ -d "$dir" ]] || { echo "Plesk-vHost fehlt: $dir" >&2; exit 4; }
  install -d -m 0700 "/root/${SERVICE}-backups"
  backup="/root/${SERVICE}-backups/vhost_nginx.pre-v7.$(date +%Y%m%d-%H%M%S).conf"
  [[ -f "$file" ]] && cp -a "$file" "$backup"
  touch "$file"
  strip_managed_block "$file"
  tmp="$(mktemp)"
  { write_locations; cat "$file"; } > "$tmp"
  cat "$tmp" > "$file"
  rm -f "$tmp"
  if ! plesk sbin httpdmng --reconfigure-domain "$HOST" >/dev/null; then
    [[ -f "$backup" ]] && cp -a "$backup" "$file"
    plesk sbin httpdmng --reconfigure-domain "$HOST" >/dev/null 2>&1 || true
    echo "Plesk-Reconfigure fehlgeschlagen; Rollback durchgeführt." >&2
    exit 5
  fi
  nginx -t
  systemctl reload nginx
  echo "Plesk V7 routing aktiv."
}

case "$MODE" in
  standalone) configure_standalone;;
  plesk) configure_plesk;;
  both)
    # On a Plesk host the public domain is owned by Plesk; route there once.
    if command -v plesk >/dev/null 2>&1; then configure_plesk; else configure_standalone; fi
    ;;
  *) echo "Unbekannter Admin-Modus: $MODE" >&2; exit 6;;
esac
