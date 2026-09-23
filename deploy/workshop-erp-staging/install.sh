#!/usr/bin/env bash
set -euo pipefail

APP=/opt/workshop-erp-staging
WEB=/opt/etes-werkstattplaner/public/jl/demo
VHOST_DIR=/var/www/vhosts/system/werkstattplaner.grow-central.de/conf
VHOST="$VHOST_DIR/vhost_nginx.conf"

command -v docker >/dev/null
docker compose version >/dev/null
command -v openssl >/dev/null
command -v curl >/dev/null

test -f docker-compose.yml
test -f src/WorkshopManager.Erp.Api/Program.cs
test -f web/index.html
test -f web/demo.js
test -f web/demo.css

mkdir -p "$APP"
DBPW=""
JWT=""
if [ -f "$APP/.env" ]; then
  set -a
  . "$APP/.env"
  set +a
  DBPW="${POSTGRES_PASSWORD:-${ERP_DB_PASSWORD:-}}"
  JWT="${WM_JWT_KEY:-${ERP_JWT_KEY:-}}"
fi
if [ "${#DBPW}" -lt 24 ]; then DBPW="$(openssl rand -hex 24)"; fi
if [ "${#JWT}" -lt 32 ]; then JWT="$(openssl rand -hex 48)"; fi

umask 077
{
  printf 'POSTGRES_PASSWORD=%s\n' "$DBPW"
  printf 'WM_JWT_KEY=%s\n' "$JWT"
  printf 'ConnectionStrings__Erp=Host=postgres;Port=5432;Database=workshop_erp_staging;Username=workshop_erp;Password=%s\n' "$DBPW"
  printf 'WM_BOOTSTRAP_ADMIN=demo\n'
  printf 'WM_BOOTSTRAP_PASSWORD=WerkstattDemo!2026\n'
} > .env
chmod 600 .env

test "${#JWT}" -ge 32
test "${#DBPW}" -ge 24

rsync -a --delete src/ "$APP/src/"
rsync -a --delete web/ "$APP/web/"
cp docker-compose.yml "$APP/docker-compose.yml"
cp .env "$APP/.env"
chmod 600 "$APP/.env"

cd "$APP"
docker compose --env-file .env up -d --build

api_ok=0
for _ in $(seq 1 90); do
  if curl -fsS http://127.0.0.1:5090/api/health >/tmp/erp-health.json; then
    api_ok=1
    break
  fi
  sleep 2
done
if [ "$api_ok" -ne 1 ]; then
  docker compose --env-file .env ps -a || true
  docker compose --env-file .env logs --tail=200 api postgres || true
  exit 1
fi

LOGIN="$(curl -fsS -H 'Content-Type: application/json'   -d '{"username":"demo","password":"WerkstattDemo!2026"}'   http://127.0.0.1:5090/api/auth/login)"
TOKEN="$(printf '%s' "$LOGIN" | python3 -c 'import json,sys; print(json.load(sys.stdin)["access_token"])')"
test -n "$TOKEN"
curl -fsS -H "Authorization: Bearer $TOKEN" http://127.0.0.1:5090/api/dashboard >/tmp/erp-dashboard.json

rm -rf "$WEB"
mkdir -p "$WEB"
cp -a "$APP/web/." "$WEB/"
find "$WEB" -type f -exec chmod 0644 {} \;
find "$WEB" -type d -exec chmod 0755 {} \;

mkdir -p "$VHOST_DIR"
python3 - "$VHOST" <<'PY'
from pathlib import Path
import re,sys
p=Path(sys.argv[1])
old=p.read_text() if p.exists() else ""
block="""# WORKSHOP_ERP_STAGING_BEGIN
error_page 419 = @workshop_erp_staging;
if ($request_uri ~ "^/jl/demo/api/") {
    return 419;
}
location @workshop_erp_staging {
    rewrite ^/jl/demo/api/(.*)$ /api/$1 break;
    proxy_pass http://127.0.0.1:5090;
    proxy_http_version 1.1;
    proxy_set_header Host $host;
    proxy_set_header X-Real-IP $remote_addr;
    proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    proxy_set_header X-Forwarded-Proto $scheme;
    proxy_read_timeout 60s;
}
# WORKSHOP_ERP_STAGING_END"""
old=re.sub(r"# WORKSHOP_ERP_STAGING_BEGIN.*?# WORKSHOP_ERP_STAGING_END","",old,flags=re.S).strip()
p.write_text((block+"\n\n"+old+"\n").lstrip())
PY

if command -v plesk >/dev/null 2>&1; then
  if plesk sbin httpdmng --reconfigure-domain werkstattplaner.grow-central.de; then
    :
  elif [ -x /usr/local/psa/admin/sbin/httpdmng ]; then
    /usr/local/psa/admin/sbin/httpdmng --reconfigure-domain werkstattplaner.grow-central.de
  else
    nginx -t
    systemctl reload nginx
  fi
else
  nginx -t
  systemctl reload nginx
fi

for _ in $(seq 1 30); do
  if curl -kfsS https://werkstattplaner.grow-central.de/jl/demo/api/health >/tmp/public-health.json; then break; fi
  sleep 2
done
curl -kfsS https://werkstattplaner.grow-central.de/jl/demo/api/health >/tmp/public-health.json
curl -kfsS https://werkstattplaner.grow-central.de/jl/demo/ | grep -q 'Workshop Manager ERP'
echo 'ERP staging deployed and verified.'
