#!/usr/bin/env bash
set -Eeuo pipefail

RAW="${RAW_V6_PAYLOAD:-https://raw.githubusercontent.com/jygnw29kms-bit/135er-Grow-Central/master/scripts/install-135ercloud-v6.payload.sh}"
TMP="$(mktemp)"
trap 'rm -f "$TMP" "$TMP.patched"' EXIT
[[ $EUID -eq 0 ]] || { echo "Bitte als root ausführen." >&2; exit 1; }

curl -fsSL "$RAW" -o "$TMP"

# The V6 application/core itself is Plesk-independent. Only its platform/vhost
# functions were hard-wired to Plesk. Insert standalone overrides immediately
# before main executes, leaving account/device/Ed25519/database logic unchanged.
python3 - "$TMP" "$TMP.patched" <<'PY'
from pathlib import Path
import sys
src=Path(sys.argv[1]).read_text()
needle='\nmain "$@"'
if needle not in src:
    raise SystemExit('V6 payload structure not recognized')
override=r'''

# ---- V7 standalone compatibility overrides ---------------------------------
detect_platform() {
  [[ -r /etc/os-release ]] || die "/etc/os-release fehlt."
  . /etc/os-release
  case "${ID:-}" in debian|ubuntu) ;; *) die "Freigegeben für Debian/Ubuntu. Erkannt: ${PRETTY_NAME:-unbekannt}";; esac
  command -v ss >/dev/null 2>&1 || true
}

configure_plesk() {
  log "Standalone-Modus: konfiguriere nginx Reverse Proxy für $CLOUD_HOST ..."
  export DEBIAN_FRONTEND=noninteractive
  command -v nginx >/dev/null 2>&1 || apt-get install -y --no-install-recommends nginx
  local conf="/etc/nginx/sites-available/135er-growcentral-cloud.conf"
  cat > "$conf" <<EOF
server {
    listen 80;
    server_name $CLOUD_HOST;
    client_max_body_size 16m;
    proxy_buffering off;
    location / {
        proxy_pass http://127.0.0.1:$APP_PORT;
        proxy_http_version 1.1;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
        proxy_set_header Upgrade \$http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_connect_timeout 15s;
        proxy_send_timeout 180s;
        proxy_read_timeout 180s;
    }
}
EOF
  ln -sfn "$conf" /etc/nginx/sites-enabled/135er-growcentral-cloud.conf
  rm -f /etc/nginx/sites-enabled/default
  nginx -t
  systemctl enable --now nginx
  systemctl reload nginx
}

get_admin_email() { echo "${LETSENCRYPT_EMAIL:-}"; }

ensure_tls_certificate() {
  if tls_valid; then return 0; fi
  local email="${LETSENCRYPT_EMAIL:-}"
  [[ -n "$email" ]] || return 2
  export DEBIAN_FRONTEND=noninteractive
  command -v certbot >/dev/null 2>&1 || apt-get install -y --no-install-recommends certbot python3-certbot-nginx
  certbot --nginx --non-interactive --agree-tos -m "$email" -d "$CLOUD_HOST" --redirect || return 2
  tls_valid
}
# ---- end standalone overrides -----------------------------------------------
'''
Path(sys.argv[2]).write_text(src.replace(needle, override+needle, 1))
PY

chmod 0755 "$TMP.patched"
exec "$TMP.patched" "$@"
