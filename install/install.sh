#!/usr/bin/env bash
set -euo pipefail

# 135er GrowControl installer baseline
# DE: Debian/Ubuntu/Raspberry-Pi-OS Installer mit sicheren Defaults.
# EN: Debian/Ubuntu/Raspberry Pi OS installer with safe defaults.

MODE="local"
DOMAIN=""
EMAIL=""
ENABLE_FIREWALL="false"

usage() {
  cat <<'EOF'
Usage: sudo ./install/install.sh [options]

  --mode local|cloud
  --domain example.org       required for automatic TLS in cloud mode
  --email admin@example.org  required for automatic TLS in cloud mode
  --enable-firewall          enable UFW after allowing SSH + HTTP/HTTPS
EOF
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --mode) MODE="$2"; shift 2 ;;
    --domain) DOMAIN="$2"; shift 2 ;;
    --email) EMAIL="$2"; shift 2 ;;
    --enable-firewall) ENABLE_FIREWALL="true"; shift ;;
    -h|--help) usage; exit 0 ;;
    *) echo "Unknown option: $1" >&2; usage; exit 2 ;;
  esac
done

if [[ $EUID -ne 0 ]]; then
  echo "Run as root / Als root ausführen." >&2
  exit 1
fi

if [[ ! -r /etc/os-release ]]; then
  echo "Unsupported OS: /etc/os-release missing" >&2
  exit 1
fi

. /etc/os-release
case "${ID}:${VERSION_ID:-}" in
  debian:12|debian:13|ubuntu:22.04|ubuntu:24.04|raspbian:*) ;;
  *)
    echo "Unsupported OS: ${PRETTY_NAME:-$ID}" >&2
    exit 1
    ;;
esac

if [[ "$MODE" != "local" && "$MODE" != "cloud" ]]; then
  echo "--mode must be local or cloud" >&2
  exit 2
fi

export DEBIAN_FRONTEND=noninteractive
apt-get update
apt-get install -y \
  ca-certificates curl git python3 python3-venv python3-pip \
  unattended-upgrades apt-listchanges jq rsync logrotate

if [[ "$MODE" == "local" ]]; then
  apt-get install -y bluetooth bluez sqlite3
else
  apt-get install -y nginx postgresql postgresql-contrib fail2ban certbot python3-certbot-nginx
  if [[ "$ENABLE_FIREWALL" == "true" ]]; then
    apt-get install -y ufw
  fi
fi

if ! id growcontrol >/dev/null 2>&1; then
  useradd --system --home /var/lib/135er-growcontrol --create-home --shell /usr/sbin/nologin growcontrol
fi

install -d -o root -g growcontrol -m 0750 /opt/135er-growcontrol
install -d -o root -g growcontrol -m 0750 /etc/135er-growcontrol
install -d -o growcontrol -g growcontrol -m 0750 /var/lib/135er-growcontrol

# DE: unattended-upgrades aktivieren. EN: enable unattended upgrades.
dpkg-reconfigure -f noninteractive unattended-upgrades || true

if [[ "$MODE" == "cloud" && "$ENABLE_FIREWALL" == "true" ]]; then
  SSH_PORT="${SSH_PORT:-22}"
  ufw allow "${SSH_PORT}/tcp"
  ufw allow 80/tcp
  ufw allow 443/tcp
  ufw --force enable
fi

if [[ "$MODE" == "cloud" && -n "$DOMAIN" && -n "$EMAIL" ]]; then
  cat >/etc/nginx/sites-available/135er-growcontrol <<EOF
server {
    listen 80;
    server_name ${DOMAIN};
    location / {
        proxy_pass http://127.0.0.1:8090;
        proxy_http_version 1.1;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-Proto \$scheme;
    }
}
EOF
  ln -sf /etc/nginx/sites-available/135er-growcontrol /etc/nginx/sites-enabled/135er-growcontrol
  nginx -t
  systemctl reload nginx
  certbot --nginx --non-interactive --agree-tos -m "$EMAIL" -d "$DOMAIN" --redirect
fi

cat <<EOF
135er GrowControl installer baseline completed.
Mode: $MODE
OS: ${PRETTY_NAME:-$ID}

DE: Quellcode-Deployment, DB-Credentials und Service-Aktivierung erfolgen im nächsten Installationsschritt.
EN: Source deployment, database credentials and service activation are handled by the next installation stage.
EOF
