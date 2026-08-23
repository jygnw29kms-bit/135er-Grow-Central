#!/usr/bin/env bash
set -Eeuo pipefail

# 135er GrowCentral Cloud V5 - Visual Installer / Repair / Finalizer
# Official endpoint: https://135ercloud.dezender.de
#
# V5 incorporates findings from the real Plesk deployment:
# - Plesk remains owner of ports 80/443
# - GrowCentral backend stays on localhost only
# - Venv permissions are normalized for the unprivileged service user
# - systemd runs "python -m uvicorn" rather than executing uvicorn directly
# - exact Let's Encrypt certificate name is used
# - reverse proxy is applied only to 135ercloud.dezender.de
# - nginx config is backed up and rolled back on failure
# - installer ends with visible OK / OK WITH WARNINGS / FAILED status
#
# Safe to rerun.

ROOT_DOMAIN="${ROOT_DOMAIN:-dezender.de}"
DOMAIN="${DOMAIN:-135ercloud.dezender.de}"
SERVICE="${SERVICE:-135er-growcentral-cloud}"
APP_USER="${APP_USER:-growcentral-cloud}"
APP_DIR="${APP_DIR:-/opt/${SERVICE}}"
DATA_DIR="${DATA_DIR:-/var/lib/${SERVICE}}"
CONF_DIR="${CONF_DIR:-/etc/${SERVICE}}"
ENV_FILE="${CONF_DIR}/cloud.env"
V4_URL="${V4_URL:-https://raw.githubusercontent.com/jygnw29kms-bit/135er-Grow-Central/master/scripts/install-135ercloud-v4.sh}"
V4_LOCAL="/root/install-135ercloud-v4-base.sh"
VHOST_DIR="/var/www/vhosts/system/${DOMAIN}/conf"
VHOST_CONF="${VHOST_DIR}/vhost_nginx.conf"
BACKUP_DIR="/root/${SERVICE}-backups"
PORT="18765"

C_RESET='\033[0m'
C_CYAN='\033[1;36m'
C_GREEN='\033[1;32m'
C_YELLOW='\033[1;33m'
C_RED='\033[1;31m'
C_WHITE='\033[1;37m'

TOTAL=12
STEP=0
WARNINGS=0
FAILED=0

header(){
  clear 2>/dev/null || true
  echo
  echo "=============================================================================="
  echo "  135er GrowCentral Cloud V5"
  echo "  VISUELLER SETUP-ASSISTENT"
  echo "=============================================================================="
  echo "  Cloud       : https://${DOMAIN}"
  echo "  Website     : https://${ROOT_DOMAIN}  (bleibt unangetastet)"
  echo "  Architektur : Plesk/nginx -> localhost GrowCentral Backend"
  echo "=============================================================================="
}

begin(){
  STEP=$((STEP+1))
  printf "\n${C_WHITE}[%02d/%02d]${C_RESET} ${C_CYAN}%s${C_RESET}\n" "$STEP" "$TOTAL" "$*"
}
pass(){ printf "        ${C_GREEN}✓ OK${C_RESET}      %s\n" "$*"; }
warn(){ WARNINGS=$((WARNINGS+1)); printf "        ${C_YELLOW}! WARN${C_RESET}    %s\n" "$*"; }
fail(){ FAILED=1; printf "        ${C_RED}✗ FAILED${C_RESET}  %s\n" "$*" >&2; }

final(){
  echo
  echo "=============================================================================="
  echo "  135er GrowCentral Cloud V5 - SETUP STATUS"
  echo "=============================================================================="
  printf "  Domain              : %s\n" "$DOMAIN"
  printf "  Backend             : 127.0.0.1:%s\n" "$PORT"
  printf "  Service             : %s\n" "$SERVICE"
  printf "  Warnungen           : %s\n" "$WARNINGS"
  echo "------------------------------------------------------------------------------"

  if [[ "$FAILED" -ne 0 ]]; then
    printf "  GESAMTSTATUS         : ${C_RED}FAILED${C_RESET}\n"
    echo "=============================================================================="
    exit 1
  elif [[ "$WARNINGS" -gt 0 ]]; then
    printf "  GESAMTSTATUS         : ${C_YELLOW}OK MIT WARNUNGEN${C_RESET}\n"
    echo "=============================================================================="
    exit 0
  else
    printf "  GESAMTSTATUS         : ${C_GREEN}OK${C_RESET}\n"
    echo "=============================================================================="
    exit 0
  fi
}

show_failure_logs(){
  echo
  echo "----- letzte GrowCentral-Logs -----"
  journalctl -u "$SERVICE" -n 60 --no-pager 2>/dev/null || true
  echo "-----------------------------------"
}

require_root(){
  if [[ "$EUID" -ne 0 ]]; then
    echo "Bitte als root ausführen."
    exit 1
  fi
}

get_port(){
  if [[ -f "$ENV_FILE" ]]; then
    local detected
    detected="$(grep '^APP_PORT=' "$ENV_FILE" 2>/dev/null | tail -1 | cut -d= -f2- || true)"
    [[ -z "$detected" ]] || PORT="$detected"
  fi
}

tls_valid(){
  echo | openssl s_client \
      -connect "${DOMAIN}:443" \
      -servername "${DOMAIN}" 2>/dev/null \
    | openssl x509 -noout -checkend 86400 >/dev/null 2>&1 \
    && echo | openssl s_client \
      -connect "${DOMAIN}:443" \
      -servername "${DOMAIN}" 2>/dev/null \
    | openssl x509 -noout -ext subjectAltName 2>/dev/null \
    | grep -Fq "DNS:${DOMAIN}"
}

get_admin_email(){
  local email=""
  email="$(plesk bin admin --info 2>/dev/null | awk -F': *' '/^Email:/ {print $2; exit}' || true)"
  if [[ -z "$email" ]]; then
    email="$(plesk db -Ne "SELECT email FROM clients WHERE login='admin' LIMIT 1" 2>/dev/null || true)"
  fi
  echo "$email"
}

rollback_proxy(){
  local backup="${1:-}"
  if [[ -n "$backup" && -f "$backup" ]]; then
    cp -a "$backup" "$VHOST_CONF"
  else
    rm -f "$VHOST_CONF"
  fi
  plesk sbin httpdmng --reconfigure-domain "$DOMAIN" >/dev/null 2>&1 || true
}

status_mode(){
  get_port
  systemctl --no-pager -l status "$SERVICE" || true
  echo
  echo "Local health:"
  curl -fsS "http://127.0.0.1:${PORT}/health" || true
  echo
  echo "Public health:"
  curl -fsS "https://${DOMAIN}/health" || true
  echo
  echo "Discovery:"
  curl -fsS "https://${DOMAIN}/.well-known/growcentral-cloud" || true
  echo
}

require_root
get_port

if [[ "${1:-}" == "--status" ]]; then
  status_mode
  exit 0
fi

header

begin "Server, Debian und Plesk prüfen"
if [[ ! -r /etc/os-release ]]; then
  fail "/etc/os-release fehlt"
  final
fi
. /etc/os-release
if [[ "${ID:-}" != "debian" && "${ID:-}" != "ubuntu" ]]; then
  fail "Nicht freigegebenes System: ${PRETTY_NAME:-unbekannt}"
  final
fi
if ! command -v plesk >/dev/null 2>&1; then
  fail "Plesk nicht gefunden"
  final
fi
if ! plesk bin domain --info "$ROOT_DOMAIN" >/dev/null 2>&1; then
  fail "Plesk-Domain ${ROOT_DOMAIN} fehlt"
  final
fi
pass "${PRETTY_NAME}; Plesk vorhanden; ${ROOT_DOMAIN} vorhanden"

begin "Benötigte Systempakete prüfen/installieren"
export DEBIAN_FRONTEND=noninteractive
if apt-get update -y >/dev/null \
   && apt-get install -y --no-install-recommends \
      ca-certificates curl wget openssl sqlite3 \
      python3 python3-venv python3-pip iproute2 util-linux >/dev/null; then
  pass "Systemabhängigkeiten sind vorhanden"
else
  fail "APT/Paketinstallation fehlgeschlagen"
  final
fi

begin "Vorhandene GrowCentral-Installation erkennen"
if [[ -f "${APP_DIR}/app.py" && -x "${APP_DIR}/venv/bin/python" && -f "$ENV_FILE" ]]; then
  pass "Vorhandene Installation erkannt; Basisinstallation wird nicht wiederholt"
else
  warn "Cloudbasis unvollständig; V4-Basisinstaller wird einmalig ausgeführt"
  if wget -qO "$V4_LOCAL" "$V4_URL"; then
    chmod +x "$V4_LOCAL"
    set +e
    "$V4_LOCAL"
    BASE_RC=$?
    set -e
    if [[ "$BASE_RC" -eq 0 ]]; then
      pass "V4-Basisinstallation abgeschlossen"
    else
      warn "V4-Basis endete mit Code ${BASE_RC}; V5 versucht automatische Reparatur"
    fi
  else
    fail "V4-Basisinstaller konnte nicht geladen werden"
    final
  fi
fi

get_port

begin "Runtime-Rechte automatisch reparieren"
if [[ ! -d "${APP_DIR}/venv" ]]; then
  fail "Python-venv fehlt unter ${APP_DIR}/venv"
  final
fi
chown -R root:"$APP_USER" "${APP_DIR}/venv" 2>/dev/null || true
chmod -R g+rX "${APP_DIR}/venv" 2>/dev/null || true
find "$APP_DIR" -maxdepth 1 -type d -name '__pycache__' -exec rm -rf {} + 2>/dev/null || true

if runuser -u "$APP_USER" -- "${APP_DIR}/venv/bin/python" -c 'import sys' >/dev/null 2>&1; then
  pass "${APP_USER} kann Python im venv ausführen"
else
  fail "Runtime-Rechte konnten nicht repariert werden"
  final
fi

begin "systemd-Dienst auf robuste Startmethode prüfen"
if [[ ! -f "/etc/systemd/system/${SERVICE}.service" ]]; then
  fail "systemd-Service fehlt"
  final
fi
sed -i \
  "s#ExecStart=${APP_DIR}/venv/bin/uvicorn app:app#ExecStart=${APP_DIR}/venv/bin/python -m uvicorn app:app#" \
  "/etc/systemd/system/${SERVICE}.service" || true

systemctl daemon-reload
systemctl enable "$SERVICE" >/dev/null 2>&1 || true
systemctl reset-failed "$SERVICE" >/dev/null 2>&1 || true
systemctl restart "$SERVICE"
sleep 2

if systemctl is-active --quiet "$SERVICE"; then
  pass "systemd-Service läuft"
else
  fail "systemd-Service startet nicht"
  show_failure_logs
  final
fi

begin "Lokalen GrowCentral-Healthcheck durchführen"
if curl -fsS "http://127.0.0.1:${PORT}/health" >/dev/null; then
  HEALTH="$(curl -fsS "http://127.0.0.1:${PORT}/health")"
  pass "Backend antwortet: ${HEALTH}"
else
  fail "Backend antwortet nicht auf 127.0.0.1:${PORT}"
  show_failure_logs
  final
fi

begin "Plesk-Subdomain prüfen/erstellen"
if plesk bin subdomain --info "$DOMAIN" >/dev/null 2>&1; then
  pass "Subdomain ${DOMAIN} existiert"
else
  SUB="${DOMAIN%.$ROOT_DOMAIN}"
  if plesk bin subdomain --create "$SUB" -domain "$ROOT_DOMAIN" \
      -php false -ssi false -cgi false -fastcgi false -ssl true >/dev/null; then
    pass "Subdomain ${DOMAIN} erstellt"
  else
    fail "Subdomain ${DOMAIN} konnte nicht erstellt werden"
    final
  fi
fi

begin "DNS-Zuordnung prüfen"
DNS_IP="$(getent ahostsv4 "$DOMAIN" 2>/dev/null | awk 'NR==1{print $1}' || true)"
SERVER_IP="$(hostname -I 2>/dev/null | awk '{print $1}')"
if [[ -n "$DNS_IP" ]]; then
  if [[ -n "$SERVER_IP" && "$DNS_IP" == "$SERVER_IP" ]]; then
    pass "${DOMAIN} -> ${DNS_IP}"
  else
    warn "${DOMAIN} -> ${DNS_IP}; lokale Haupt-IP ist ${SERVER_IP:-unbekannt}"
  fi
else
  warn "DNS ist noch nicht auflösbar; TLS kann ggf. noch nicht ausgestellt werden"
fi

begin "Let's-Encrypt-Zertifikat prüfen/einrichten"
if tls_valid; then
  pass "Gültiges Zertifikat für exakt ${DOMAIN} ist aktiv"
else
  ADMIN_EMAIL="$(get_admin_email)"
  if [[ -z "$ADMIN_EMAIL" ]]; then
    warn "Plesk-Admin-Mail konnte nicht automatisch ermittelt werden"
  else
    echo "        Fordere Zertifikat mit ${ADMIN_EMAIL} an ..."
    if plesk bin extension --exec letsencrypt cli.php -d "$DOMAIN" -m "$ADMIN_EMAIL"; then
      CERT_NAME="Lets Encrypt ${DOMAIN}"
      if plesk bin certificate --list -domain "$DOMAIN" 2>/dev/null | grep -Fq "$CERT_NAME"; then
        plesk bin site -u "$DOMAIN" -certificate-name "$CERT_NAME" >/dev/null 2>&1 || true
      fi
      plesk sbin httpdmng --reconfigure-domain "$DOMAIN" >/dev/null 2>&1 || true
      systemctl reload nginx >/dev/null 2>&1 || true
      sleep 1
      if tls_valid; then
        pass "Let's Encrypt aktiv; SAN enthält ${DOMAIN}"
      else
        warn "Zertifikat angefordert, aber externe Validierung noch nicht erfolgreich"
      fi
    else
      warn "Let's-Encrypt-Ausstellung fehlgeschlagen"
    fi
  fi
fi

begin "Plesk Reverse Proxy sicher einrichten"
mkdir -p "$VHOST_DIR" "$BACKUP_DIR"
STAMP="$(date +%Y%m%d-%H%M%S)"
PROXY_BACKUP=""
if [[ -f "$VHOST_CONF" ]]; then
  PROXY_BACKUP="${BACKUP_DIR}/vhost_nginx.conf.${STAMP}"
  cp -a "$VHOST_CONF" "$PROXY_BACKUP"
fi

cat > "$VHOST_CONF" <<EOF
# 135er GrowCentral Cloud V5 - managed reverse proxy
location ~ ^/.* {
    proxy_pass http://127.0.0.1:${PORT};
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

    proxy_buffering off;
    client_max_body_size 16m;
}
EOF
chmod 0644 "$VHOST_CONF"

if ! plesk sbin httpdmng --reconfigure-domain "$DOMAIN"; then
  rollback_proxy "$PROXY_BACKUP"
  fail "Plesk-vHost konnte nicht neu erzeugt werden; Rollback ausgeführt"
  final
fi

if ! nginx -t; then
  rollback_proxy "$PROXY_BACKUP"
  fail "nginx-Konfiguration ungültig; Rollback ausgeführt"
  final
fi

systemctl reload nginx
pass "Reverse Proxy aktiv; nginx-Konfiguration gültig"

begin "Öffentlichen HTTPS-Healthcheck prüfen"
if curl -fsS --connect-timeout 10 "https://${DOMAIN}/health" >/dev/null 2>&1; then
  PUBLIC_HEALTH="$(curl -fsS "https://${DOMAIN}/health")"
  pass "Öffentliche API erreichbar: ${PUBLIC_HEALTH}"
else
  warn "HTTPS-Healthcheck noch nicht erfolgreich"
fi

begin "GrowCentral Discovery und WSS-Endpunkte prüfen"
if DISCOVERY="$(curl -fsS --connect-timeout 10 "https://${DOMAIN}/.well-known/growcentral-cloud" 2>/dev/null)"; then
  if echo "$DISCOVERY" | grep -Fq "wss://${DOMAIN}/api/v2/device/connect" \
     && echo "$DISCOVERY" | grep -Fq "wss://${DOMAIN}/api/v2/remote/connect"; then
    pass "Discovery + Device-WSS + Remote-WSS veröffentlicht"
  else
    warn "Discovery erreichbar, erwartete WSS-Endpunkte aber nicht vollständig enthalten"
  fi
else
  warn "Discovery-Endpunkt noch nicht öffentlich erreichbar"
fi

begin "Abschlussprüfung"
LOCAL_OK=0
SERVICE_OK=0
PUBLIC_OK=0
DISCOVERY_OK=0
TLS_OK=0

systemctl is-active --quiet "$SERVICE" && SERVICE_OK=1
curl -fsS "http://127.0.0.1:${PORT}/health" >/dev/null 2>&1 && LOCAL_OK=1
curl -fsS "https://${DOMAIN}/health" >/dev/null 2>&1 && PUBLIC_OK=1
curl -fsS "https://${DOMAIN}/.well-known/growcentral-cloud" >/dev/null 2>&1 && DISCOVERY_OK=1
tls_valid && TLS_OK=1

echo
printf "        Service        : %s\n" "$([[ $SERVICE_OK -eq 1 ]] && echo OK || echo FAILED)"
printf "        Backend lokal  : %s\n" "$([[ $LOCAL_OK -eq 1 ]] && echo OK || echo FAILED)"
printf "        HTTPS öffentlich: %s\n" "$([[ $PUBLIC_OK -eq 1 ]] && echo OK || echo WARN)"
printf "        TLS Zertifikat : %s\n" "$([[ $TLS_OK -eq 1 ]] && echo OK || echo WARN)"
printf "        Discovery/WSS  : %s\n" "$([[ $DISCOVERY_OK -eq 1 ]] && echo OK || echo WARN)"

if [[ $SERVICE_OK -eq 1 && $LOCAL_OK -eq 1 ]]; then
  pass "Kernsystem funktionsfähig"
else
  fail "Kernsystem nicht funktionsfähig"
fi

if [[ $PUBLIC_OK -ne 1 || $TLS_OK -ne 1 || $DISCOVERY_OK -ne 1 ]]; then
  warn "Mindestens eine öffentliche Prüfung benötigt noch Aufmerksamkeit"
fi

final
