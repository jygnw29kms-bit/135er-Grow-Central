#!/usr/bin/env bash
set -Eeuo pipefail

SERVICE="${SERVICE:-135er-growcentral-cloud}"
CONF_DIR="${CONF_DIR:-/etc/${SERVICE}}"
ENV_FILE="${ENV_FILE:-${CONF_DIR}/cloud.env}"
MODE_FILE="${MODE_FILE:-${CONF_DIR}/admin-mode}"
CANONICAL_HOST="${GC_CANONICAL_CLOUD_HOST:-135ercloud.grow-central.de}"
[[ $EUID -eq 0 ]] || { echo "Bitte als root ausführen." >&2; exit 1; }
[[ -r "$ENV_FILE" ]] || { echo "$ENV_FILE fehlt." >&2; exit 1; }

set -a
# shellcheck disable=SC1090
. "$ENV_FILE"
set +a
MODE="$(cat "$MODE_FILE" 2>/dev/null || printf '%s' "${CLOUD_ADMIN_MODE:-standalone}")"

detect_core_port(){
  local candidate exec_line port
  candidate="${APP_PORT:-}"
  if [[ "$candidate" =~ ^[0-9]{2,5}$ ]] && curl -fsS --connect-timeout 2 "http://127.0.0.1:${candidate}/health" >/dev/null 2>&1; then
    printf '%s' "$candidate"
    return 0
  fi
  exec_line="$(systemctl show "$SERVICE" -p ExecStart --value 2>/dev/null || true)"
  port="$(printf '%s\n' "$exec_line" | sed -nE 's/.*--port[ =]+([0-9]{2,5}).*/\1/p' | head -n1)"
  if [[ "$port" =~ ^[0-9]{2,5}$ ]] && curl -fsS --connect-timeout 2 "http://127.0.0.1:${port}/health" >/dev/null 2>&1; then
    printf '%s' "$port"
    return 0
  fi
  for candidate in 18765 18766 18767 18768 18769 18770 18771 18772; do
    [[ "$candidate" == "${V7_ADMIN_PORT:-}" || "$candidate" == "${V7_PLATFORM_PORT:-}" ]] && continue
    if curl -fsS --connect-timeout 1 "http://127.0.0.1:${candidate}/health" 2>/dev/null \
      | python3 -c 'import json,sys; d=json.load(sys.stdin); assert d.get("ok") is True and d.get("service") == "135er-growcentral-cloud"' 2>/dev/null; then
      printf '%s' "$candidate"
      return 0
    fi
  done
  echo "Core-Port von ${SERVICE} konnte nicht ermittelt werden." >&2
  return 1
}

CORE_PORT="$(detect_core_port)"
ADMIN_PORT="${V7_ADMIN_PORT:?V7_ADMIN_PORT fehlt}"
PLATFORM_PORT="${V7_PLATFORM_PORT:-18767}"
HOST="${PUBLIC_URL#https://}"; HOST="${HOST#http://}"; HOST="${HOST%%/*}"

# grow-central.de is the canonical project domain. Prefer the canonical Plesk
# vhost whenever it exists while retaining a configured transitional host as
# a safe deployment fallback.
if command -v plesk >/dev/null 2>&1 && [[ -d "/var/www/vhosts/system/${CANONICAL_HOST}/conf" ]]; then
  HOST="$CANONICAL_HOST"
fi

write_locations(){
  cat <<EOF
# BEGIN 135ER-GROWCENTRAL-V7
# Current V7 services coexist with the V6 account/device core.  Keep these
# routes explicit in Plesk mode; do not depend on an older catch-all block.
location = /api/health {
    proxy_pass http://127.0.0.1:${PLATFORM_PORT}/api/health;
    proxy_http_version 1.1;
    proxy_set_header Host \$host;
    proxy_set_header X-Forwarded-Proto \$scheme;
}
location = /health {
    proxy_pass http://127.0.0.1:${CORE_PORT}/health;
    proxy_http_version 1.1;
    proxy_set_header Host \$host;
    proxy_set_header X-Real-IP \$remote_addr;
    proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
    proxy_set_header X-Forwarded-Proto \$scheme;
}
location = /.well-known/growcentral-cloud {
    proxy_pass http://127.0.0.1:${PLATFORM_PORT}/.well-known/growcentral-cloud;
    proxy_http_version 1.1;
    proxy_set_header Host \$host;
    proxy_set_header X-Forwarded-Proto \$scheme;
}
location = /pair {
    proxy_pass http://127.0.0.1:${CORE_PORT};
    proxy_http_version 1.1;
    proxy_set_header Host \$host;
    proxy_set_header X-Real-IP \$remote_addr;
    proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
    proxy_set_header X-Forwarded-Proto \$scheme;
}
location ^~ /api/v2/ {
    proxy_pass http://127.0.0.1:${CORE_PORT};
    proxy_http_version 1.1;
    proxy_set_header Host \$host;
    proxy_set_header X-Real-IP \$remote_addr;
    proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
    proxy_set_header X-Forwarded-Proto \$scheme;
    proxy_set_header Upgrade \$http_upgrade;
    proxy_set_header Connection "upgrade";
    proxy_buffering off;
}
location ^~ /api/v7/platform/ {
    proxy_pass http://127.0.0.1:${PLATFORM_PORT};
    proxy_http_version 1.1;
    proxy_set_header Host \$host;
    proxy_set_header X-Real-IP \$remote_addr;
    proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
    proxy_set_header X-Forwarded-Proto \$scheme;
    proxy_buffering off;
}
location = /api/admin/platform {
    proxy_pass http://127.0.0.1:${PLATFORM_PORT}/api/admin/platform;
    proxy_http_version 1.1;
    proxy_set_header Host \$host;
    proxy_set_header X-Real-IP \$remote_addr;
    proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
    proxy_set_header X-Forwarded-Proto \$scheme;
    proxy_buffering off;
}
location = /platform/health {
    proxy_pass http://127.0.0.1:${PLATFORM_PORT}/health;
}
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
s=re.sub(r"(?ms)^# BEGIN 135ER-GROWCENTRAL-V7-PROXY-LIMIT\n.*?^# END 135ER-GROWCENTRAL-V7-PROXY-LIMIT\n?", "", s)
s=re.sub(r"(?ms)^# BEGIN 135ER-GROWCENTRAL-V7\n.*?^# END 135ER-GROWCENTRAL-V7\n?", "", s)
p.write_text(s)
PY
}

clean_legacy_plesk_limit(){
  python3 - "$1" <<'PY'
from pathlib import Path
import re,sys
p=Path(sys.argv[1])
lines=p.read_text().splitlines() if p.exists() else []
out=[]
for line in lines:
    # Older Grow-Central installers wrote an unmarked 40m directive directly
    # into Plesk's custom vhost file. Plesk can already provide its own limit,
    # and nginx rejects both at the same level. Remove only our known legacy
    # value; preserve any operator-defined value that differs from 40m.
    if re.fullmatch(r"\s*client_max_body_size\s+40m\s*;\s*", line):
        continue
    out.append(line)
p.write_text(("\n".join(out).rstrip()+"\n") if out else "")
PY
}

configure_standalone(){
  command -v nginx >/dev/null 2>&1 || { echo "nginx fehlt." >&2; exit 2; }
  local conf="/etc/nginx/sites-available/135er-growcentral-cloud.conf"
  cat > "$conf" <<EOF
server {
    listen 80;
    server_name ${HOST};
    # Pi support bundles are capped at 32 MiB in the cloud-link agent. Keep
    # nginx above that limit so valid diagnostics never fail at the proxy.
    client_max_body_size 40m;
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

normalize_core_public_url(){
  local expected="https://${CANONICAL_HOST}" current backup
  current="${PUBLIC_URL:-}"
  [[ "$HOST" == "$CANONICAL_HOST" ]] || return 0
  [[ "$current" == "$expected" ]] && return 0
  install -d -m 0700 "/root/${SERVICE}-backups"
  backup="/root/${SERVICE}-backups/cloud.env.pre-canonical.$(date +%Y%m%d-%H%M%S)"
  cp -a "$ENV_FILE" "$backup"
  EXPECTED_PUBLIC_URL="$expected" python3 - "$ENV_FILE" <<'PY'
from pathlib import Path
import os,sys
p=Path(sys.argv[1])
lines=p.read_text().splitlines()
value=os.environ["EXPECTED_PUBLIC_URL"]
out=[]
seen=False
for line in lines:
    if line.startswith("PUBLIC_URL="):
        if not seen:
            out.append("PUBLIC_URL="+value)
            seen=True
        continue
    out.append(line)
if not seen:
    out.append("PUBLIC_URL="+value)
p.write_text("\n".join(out).rstrip()+"\n")
PY
  PUBLIC_URL="$expected"
  export PUBLIC_URL
  if systemctl restart "$SERVICE" && sleep 1 && curl -fsS --connect-timeout 5 "http://127.0.0.1:${CORE_PORT}/health" >/dev/null; then
    echo "Grow-Central Core PUBLIC_URL auf ${expected} vereinheitlicht."
    return 0
  fi
  cp -a "$backup" "$ENV_FILE"
  systemctl restart "$SERVICE" >/dev/null 2>&1 || true
  echo "Canonical-PUBLIC_URL fehlgeschlagen; cloud.env wurde zurueckgerollt." >&2
  return 1
}

configure_plesk(){
  command -v plesk >/dev/null 2>&1 || { echo "Plesk-Modus gewählt, Plesk fehlt." >&2; exit 3; }
  local dir="/var/www/vhosts/system/${HOST}/conf" file backup tmp
  file="$dir/vhost_nginx.conf"
  [[ -d "$dir" ]] || { echo "Plesk-vHost fehlt: $dir" >&2; exit 4; }
  install -d -m 0700 "/root/${SERVICE}-backups"
  normalize_core_public_url
  backup="/root/${SERVICE}-backups/vhost_nginx.pre-v7.$(date +%Y%m%d-%H%M%S).conf"
  [[ -f "$file" ]] && cp -a "$file" "$backup"
  touch "$file"
  strip_managed_block "$file"
  clean_legacy_plesk_limit "$file"
  tmp="$(mktemp)"
  {
    # Plesk owns client_max_body_size in Plesk mode. Grow Central only owns
    # the reverse-proxy locations below; this keeps the custom vhost idempotent.
    write_locations
    cat "$file"
  } > "$tmp"
  cat "$tmp" > "$file"
  rm -f "$tmp"
  echo "Grow-Central Plesk Routing-Ziel: ${HOST}"
  if ! plesk sbin httpdmng --reconfigure-domain "$HOST" >/dev/null; then
    [[ -f "$backup" ]] && cp -a "$backup" "$file"
    plesk sbin httpdmng --reconfigure-domain "$HOST" >/dev/null 2>&1 || true
    echo "Plesk-Reconfigure fehlgeschlagen; Rollback durchgeführt." >&2
    exit 5
  fi
  nginx -t
  systemctl reload nginx
  echo "Plesk V7 routing aktiv für ${HOST}."
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
