#!/usr/bin/env bash
set -Eeuo pipefail

SERVICE="${SERVICE:-135er-growcentral-cloud}"
ADMIN_SERVICE="${ADMIN_SERVICE:-135er-growcentral-cloud-admin}"
APP_USER="${APP_USER:-growcentral-cloud}"
APP_DIR="${APP_DIR:-/opt/${SERVICE}}"
DATA_DIR="${DATA_DIR:-/var/lib/${SERVICE}}"
CONF_DIR="${CONF_DIR:-/etc/${SERVICE}}"
ENV_FILE="${ENV_FILE:-${CONF_DIR}/cloud.env}"
MODE_FILE="${MODE_FILE:-${CONF_DIR}/admin-mode}"
BACKUP_DIR="${BACKUP_DIR:-/root/${SERVICE}-backups}"
SYSTEMD_ADMIN="/etc/systemd/system/${ADMIN_SERVICE}.service"
V7_SOURCE="${V7_SOURCE:-/usr/lib/${SERVICE}/v7/admin_app.py}"
MODE_HELPER="${MODE_HELPER:-/usr/lib/${SERVICE}/configure-cloud-admin-mode.sh}"
V6_INSTALLER="${V6_INSTALLER:-/usr/lib/${SERVICE}/install-135ercloud-v6.sh}"
GITHUB_RAW="https://raw.githubusercontent.com/jygnw29kms-bit/135er-Grow-Central/master"
PACKAGE_MODE=0
REQUESTED_MODE=""

log(){ printf '\033[1;36m[GrowCentral V7]\033[0m %s\n' "$*"; }
ok(){ printf '\033[1;32m[OK]\033[0m %s\n' "$*"; }
warn(){ printf '\033[1;33m[WARN]\033[0m %s\n' "$*"; }
die(){ printf '\033[1;31m[FEHLER]\033[0m %s\n' "$*" >&2; exit 1; }

while [[ $# -gt 0 ]]; do
  case "$1" in
    --package-mode) PACKAGE_MODE=1; shift;;
    --admin-mode) REQUESTED_MODE="${2:-}"; shift 2;;
    -h|--help)
      cat <<'EOF'
135er Grow Central Cloud V7 Installer/Upgrade

  --package-mode                     non-interactive APT postinst mode
  --admin-mode standalone|plesk|both explicit admin mode

Existing V6 data and secrets are preserved. A backup is created before changes.
EOF
      exit 0;;
    *) die "Unbekannte Option: $1";;
  esac
done

[[ $EUID -eq 0 ]] || die "Bitte als root ausführen."

source_env(){
  [[ -r "$ENV_FILE" ]] || return 1
  set -a
  # shellcheck disable=SC1090
  . "$ENV_FILE"
  set +a
}

append_env_if_missing(){
  local key="$1" value="$2"
  grep -q "^${key}=" "$ENV_FILE" 2>/dev/null || printf '%s=%s\n' "$key" "$value" >> "$ENV_FILE"
}

backup_current(){
  local stamp dir db_path
  stamp="$(date +%Y%m%d-%H%M%S)"
  dir="$BACKUP_DIR/v7-upgrade-$stamp"
  install -d -m 0700 "$dir"
  if [[ -f "$ENV_FILE" ]]; then
    cp -a "$ENV_FILE" "$dir/cloud.env"
  fi
  if [[ -f "$MODE_FILE" ]]; then cp -a "$MODE_FILE" "$dir/admin-mode"; fi
  if [[ -f "$APP_DIR/app.py" ]]; then cp -a "$APP_DIR/app.py" "$dir/app-v6.py"; fi
  if source_env; then
    if [[ "${DATABASE_URL:-}" == sqlite:////* ]]; then
      db_path="/${DATABASE_URL#sqlite:////}"
      if [[ -f "$db_path" ]] && command -v sqlite3 >/dev/null 2>&1; then
        sqlite3 "$db_path" ".backup '$dir/cloud.sqlite3'" || warn "SQLite Online-Backup fehlgeschlagen"
      fi
    elif [[ "${DATABASE_URL:-}" == postgresql* ]] && command -v pg_dump >/dev/null 2>&1; then
      pg_dump "${DATABASE_URL/postgresql+psycopg:/postgresql:}" > "$dir/cloud.sql" 2>/dev/null || warn "PostgreSQL-Backup fehlgeschlagen"
    fi
  fi
  printf '%s\n' "$dir" > "$CONF_DIR/last-v7-backup"
  ok "Backup: $dir"
}

ensure_v6(){
  if systemctl cat "$SERVICE" >/dev/null 2>&1 && [[ -f "$ENV_FILE" && -f "$APP_DIR/app.py" ]]; then
    ok "Bestehende V6/Cloud-Instanz erkannt"
    return 0
  fi
  log "Keine bestehende Cloud-Instanz erkannt; installiere V6-Core als kompatible Basis."
  if [[ ! -x "$V6_INSTALLER" ]]; then
    install -d -m 0755 "$(dirname "$V6_INSTALLER")"
    curl -fsSL "$GITHUB_RAW/scripts/install-135ercloud-v6.sh" -o "$V6_INSTALLER"
    chmod 0755 "$V6_INSTALLER"
  fi
  if [[ "$PACKAGE_MODE" -eq 1 ]]; then "$V6_INSTALLER" --package-mode; else "$V6_INSTALLER"; fi
  [[ -f "$ENV_FILE" ]] || die "V6-Basisinstallation hat keine cloud.env erzeugt"
}

install_mode_helper(){
  if [[ ! -x "$MODE_HELPER" ]]; then
    install -d -m 0755 "$(dirname "$MODE_HELPER")"
    curl -fsSL "$GITHUB_RAW/scripts/configure-cloud-admin-mode.sh" -o "$MODE_HELPER"
    chmod 0755 "$MODE_HELPER"
  fi
  if [[ -n "$REQUESTED_MODE" ]]; then
    "$MODE_HELPER" --mode "$REQUESTED_MODE" --noninteractive
  elif [[ "$PACKAGE_MODE" -eq 1 ]]; then
    "$MODE_HELPER" --noninteractive
  else
    "$MODE_HELPER"
  fi
}

choose_admin_port(){
  source_env || die "cloud.env konnte nicht geladen werden"
  local p core="${APP_PORT:-18765}"
  if [[ -n "${V7_ADMIN_PORT:-}" ]]; then printf '%s\n' "$V7_ADMIN_PORT"; return; fi
  for p in $((core+1)) $((core+2)) 18790 18791 18792; do
    if ! ss -ltnH 2>/dev/null | awk '{print $4}' | grep -Eq "(:|\])${p}$"; then printf '%s\n' "$p"; return; fi
  done
  die "Kein freier interner V7-Admin-Port gefunden"
}

install_v7_source(){
  local target="$APP_DIR/admin_v7.py"
  if [[ ! -f "$V7_SOURCE" ]]; then
    install -d -m 0755 "$(dirname "$V7_SOURCE")"
    curl -fsSL "$GITHUB_RAW/cloud/v7/admin_app.py" -o "$V7_SOURCE"
  fi
  install -m 0644 -o root -g root "$V7_SOURCE" "$target"
  ok "V7 Admin-Sidecar installiert"
}

ensure_env(){
  local port="$1"
  touch "$ENV_FILE"
  append_env_if_missing CLOUD_ADMIN_TOKEN "$(openssl rand -hex 32)"
  append_env_if_missing CLOUD_ADMIN_MODE "$(cat "$MODE_FILE" 2>/dev/null || echo standalone)"
  append_env_if_missing CLOUD_MAX_DEVICES "1000"
  append_env_if_missing CLOUD_HEARTBEAT_SECONDS "30"
  append_env_if_missing CLOUD_OFFLINE_AFTER_SECONDS "120"
  append_env_if_missing V7_ADMIN_PORT "$port"
  chown root:"$APP_USER" "$ENV_FILE" 2>/dev/null || true
  chmod 0640 "$ENV_FILE"
}

write_systemd(){
  source_env || die "cloud.env konnte nicht geladen werden"
  local port="${V7_ADMIN_PORT:?}"
  cat > "$SYSTEMD_ADMIN" <<EOF
[Unit]
Description=135er Grow Central Cloud V7 Administration
After=${SERVICE}.service network-online.target
Requires=${SERVICE}.service

[Service]
Type=simple
User=${APP_USER}
Group=${APP_USER}
EnvironmentFile=${ENV_FILE}
WorkingDirectory=${APP_DIR}
ExecStart=${APP_DIR}/venv/bin/python -m uvicorn admin_v7:app --host 127.0.0.1 --port ${port} --proxy-headers --forwarded-allow-ips=127.0.0.1
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
  systemctl enable "$ADMIN_SERVICE" >/dev/null
  systemctl restart "$ADMIN_SERVICE"
  sleep 1
  systemctl is-active --quiet "$ADMIN_SERVICE" || die "V7 Admin-Service startet nicht"
  ok "$ADMIN_SERVICE aktiv auf 127.0.0.1:$port"
}

write_standalone_nginx(){
  source_env || return 0
  local mode="${CLOUD_ADMIN_MODE:-standalone}" host core admin conf
  [[ "$mode" == standalone || "$mode" == both ]] || return 0
  command -v nginx >/dev/null 2>&1 || { warn "nginx fehlt; Standalone-Reverse-Proxy wird erst nach Installation von nginx aktiviert"; return 0; }
  host="${PUBLIC_URL#https://}"; host="${host#http://}"; host="${host%%/*}"
  core="${APP_PORT:-18765}"; admin="${V7_ADMIN_PORT}"
  conf="/etc/nginx/sites-available/135er-growcentral-cloud.conf"
  cat > "$conf" <<EOF
server {
    listen 80;
    server_name ${host};
    client_max_body_size 2m;
    location /admin { proxy_pass http://127.0.0.1:${admin}; proxy_set_header Host \$host; proxy_set_header X-Forwarded-Proto \$scheme; }
    location /api/admin/ { proxy_pass http://127.0.0.1:${admin}; proxy_set_header Host \$host; proxy_set_header X-Forwarded-Proto \$scheme; }
    location /v7/health { proxy_pass http://127.0.0.1:${admin}/health; }
    location / { proxy_pass http://127.0.0.1:${core}; proxy_http_version 1.1; proxy_set_header Upgrade \$http_upgrade; proxy_set_header Connection "upgrade"; proxy_set_header Host \$host; proxy_set_header X-Forwarded-Proto \$scheme; }
}
EOF
  ln -sfn "$conf" /etc/nginx/sites-enabled/135er-growcentral-cloud.conf
  nginx -t && systemctl reload nginx
  ok "Standalone-nginx konfiguriert (HTTP; TLS kann anschließend über Zertifikatsverwaltung aktiviert werden)"
}

write_plesk_hint(){
  source_env || return 0
  local mode="${CLOUD_ADMIN_MODE:-standalone}"
  if [[ "$mode" == plesk || "$mode" == both ]]; then
    if command -v plesk >/dev/null 2>&1; then
      ok "Plesk erkannt; V7-Datenbasis ist für die Plesk-Extension verfügbar"
    else
      warn "Plesk-Modus gespeichert, aber Plesk ist aktuell nicht vorhanden"
    fi
  fi
}

healthcheck(){
  source_env || die "cloud.env nicht lesbar"
  curl -fsS --connect-timeout 4 "http://127.0.0.1:${V7_ADMIN_PORT}/health" >/dev/null || die "V7 Healthcheck fehlgeschlagen"
  curl -fsS --connect-timeout 4 "http://127.0.0.1:${APP_PORT:-18765}/health" >/dev/null || warn "V6-Core-Healthcheck nicht unter /health erreichbar"
  ok "V7 Healthcheck erfolgreich"
}

main(){
  export DEBIAN_FRONTEND="${DEBIAN_FRONTEND:-noninteractive}"
  install -d -m 0750 "$CONF_DIR"
  install -d -m 0700 "$BACKUP_DIR"
  ensure_v6
  backup_current
  install_mode_helper
  local admin_port
  admin_port="$(choose_admin_port)"
  ensure_env "$admin_port"
  install_v7_source
  write_systemd
  write_standalone_nginx
  write_plesk_hint
  healthcheck
  echo
  echo "=============================================================================="
  echo "  135er Grow Central Cloud V7"
  echo "=============================================================================="
  echo "  Upgrade       : erfolgreich"
  echo "  V6-Core       : erhalten"
  echo "  Admin-Modus   : $(cat "$MODE_FILE" 2>/dev/null || echo standalone)"
  echo "  Admin-Service : $ADMIN_SERVICE"
  echo "  APT-fähig     : ja"
  echo "  Backup        : $(cat "$CONF_DIR/last-v7-backup" 2>/dev/null || echo unbekannt)"
  echo "=============================================================================="
}

main "$@"
