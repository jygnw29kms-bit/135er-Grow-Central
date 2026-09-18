#!/usr/bin/env bash
set -Eeuo pipefail

DOMAIN="grow-central.de"
REPO_URL="https://grow-central.de/apt/135er-growcentral"
REPO_ROOT="/var/www/vhosts/grow-central.de/httpdocs/apt/135er-growcentral"
SRC_URL="https://raw.githubusercontent.com/jygnw29kms-bit/135er-Grow-Central/master/scripts/install-135ercloud-v4.sh"
GNUPGHOME="/root/.gnupg-135er-growcentral-repo"
KEY_NAME="135er GrowCentral APT Repository <repo@grow-central.de>"
VERSION="${VERSION:-5.1.0-1}"

G='\033[1;32m'; Y='\033[1;33m'; R='\033[0m'; C='\033[1;36m'
ok(){ echo -e "      ${G}✓ OK${R} $*"; }
warn(){ echo -e "      ${Y}! WARN${R} $*"; }
step(){ echo; echo -e "${C}$*${R}"; }

[[ $EUID -eq 0 ]] || { echo "Als root ausführen."; exit 1; }
command -v plesk >/dev/null || { echo "Plesk fehlt."; exit 1; }
plesk bin domain --info "$DOMAIN" >/dev/null 2>&1 || { echo "Plesk-Domain $DOMAIN fehlt."; exit 1; }

echo
echo "=============================================================================="
echo "  135er GrowCentral APT Repository - Erstaufbau"
echo "=============================================================================="
echo "  $REPO_URL"
echo "=============================================================================="

step "[1/8] Werkzeuge installieren"
apt-get update -y
apt-get install -y --no-install-recommends dpkg-dev apt-utils gnupg python3 curl ca-certificates
ok "Werkzeuge bereit"

step "[2/8] GrowCentral-Quellstand laden"
TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT
curl -fsSL "$SRC_URL" -o "$TMP/base.sh"
python3 - "$TMP/base.sh" "$TMP/app.py" <<'PY'
import re,sys
src=open(sys.argv[1],encoding="utf-8").read()
m=re.search(r'cat > "\$APP_DIR/app\.py" <<\x27PY\x27\n(.*?)\nPY\n',src,re.S)
if not m: raise SystemExit("app.py im Basisskript nicht gefunden")
open(sys.argv[2],"w",encoding="utf-8").write(m.group(1))
PY
python3 -m py_compile "$TMP/app.py"
ok "Cloud-App extrahiert und geprüft"

step "[3/8] Selbstständiges Debian-Paket bauen"
PKG="$TMP/pkg"
mkdir -p "$PKG/DEBIAN" "$PKG/usr/lib/135er-growcentral-cloud" "$PKG/usr/sbin" "$PKG/lib/systemd/system"
chmod 0755 "$PKG/DEBIAN"
install -m 0644 "$TMP/app.py" "$PKG/usr/lib/135er-growcentral-cloud/app.py"

cat > "$PKG/DEBIAN/control" <<EOF
Package: 135er-growcentral-cloud
Version: $VERSION
Section: net
Priority: optional
Architecture: all
Maintainer: 135er GrowCentral <repo@grow-central.de>
Depends: python3, python3-fastapi, python3-uvicorn, python3-sqlalchemy, python3-argon2, python3-cryptography, python3-multipart, curl, openssl, sqlite3, iproute2, ca-certificates, util-linux
Description: 135er GrowCentral Cloud server
 Secure GrowCentral cloud relay for Plesk servers.
EOF

cat > "$PKG/lib/systemd/system/135er-growcentral-cloud.service" <<'EOF'
[Unit]
Description=135er GrowCentral Cloud
After=network-online.target
Wants=network-online.target

[Service]
Type=simple
User=growcentral-cloud
Group=growcentral-cloud
EnvironmentFile=/etc/135er-growcentral-cloud/cloud.env
WorkingDirectory=/usr/lib/135er-growcentral-cloud
ExecStart=/usr/bin/python3 -m uvicorn app:app --host 127.0.0.1 --port 18765 --proxy-headers --forwarded-allow-ips=127.0.0.1
Restart=on-failure
RestartSec=3
NoNewPrivileges=true
PrivateTmp=true
PrivateDevices=true
ProtectSystem=strict
ProtectHome=true
ReadWritePaths=/var/lib/135er-growcentral-cloud
ProtectKernelTunables=true
ProtectKernelModules=true
ProtectControlGroups=true
RestrictSUIDSGID=true
LockPersonality=true
UMask=0077

[Install]
WantedBy=multi-user.target
EOF

cat > "$PKG/usr/lib/135er-growcentral-cloud/setup.sh" <<'EOF'
#!/usr/bin/env bash
set -Eeuo pipefail
DOMAIN="135ercloud.grow-central.de"; ROOT_DOMAIN="grow-central.de"; SERVICE="135er-growcentral-cloud"
APP_USER="growcentral-cloud"; DATA="/var/lib/135er-growcentral-cloud"; CONF="/etc/135er-growcentral-cloud"; ENV="$CONF/cloud.env"
VHOST="/var/www/vhosts/system/$DOMAIN/conf/vhost_nginx.conf"; PORT=18765
G='\033[1;32m';Y='\033[1;33m';X='\033[1;31m';R='\033[0m';C='\033[1;36m'
TOTAL=9;N=0;W=0;F=0
step(){ N=$((N+1)); printf "\n[%02d/%02d] ${C}%s${R}\n" "$N" "$TOTAL" "$*"; }
ok(){ echo -e "       ${G}✓ OK${R} $*"; }; warn(){ W=$((W+1));echo -e "       ${Y}! WARN${R} $*";}; fail(){F=1;echo -e "       ${X}✗ FAILED${R} $*" >&2;}
finish(){ echo;echo "==============================================================================";echo "  135er GrowCentral Cloud - SETUP STATUS";echo "==============================================================================";echo "  Domain      : $DOMAIN";echo "  Backend     : 127.0.0.1:$PORT";echo "  Warnungen   : $W";echo "------------------------------------------------------------------------------";if [ "$F" -ne 0 ];then echo -e "  GESAMTSTATUS: ${X}FAILED${R}";exit 1;elif [ "$W" -gt 0 ];then echo -e "  GESAMTSTATUS: ${Y}OK MIT WARNUNGEN${R}";else echo -e "  GESAMTSTATUS: ${G}OK${R}";fi;echo "==============================================================================";}
tls(){ echo|openssl s_client -connect "$DOMAIN:443" -servername "$DOMAIN" 2>/dev/null|openssl x509 -noout -checkend 86400 >/dev/null 2>&1 && echo|openssl s_client -connect "$DOMAIN:443" -servername "$DOMAIN" 2>/dev/null|openssl x509 -noout -ext subjectAltName 2>/dev/null|grep -Fq "DNS:$DOMAIN"; }
echo;echo "==============================================================================";echo "  135er GrowCentral Cloud - APT Installation/Update";echo "=============================================================================="
step "Plesk prüfen"; command -v plesk >/dev/null && plesk bin domain --info "$ROOT_DOMAIN" >/dev/null 2>&1 && ok "Plesk + $ROOT_DOMAIN" || { fail "Plesk/Domain fehlt";finish; }
step "Daten/Secrets vorbereiten"; id "$APP_USER" >/dev/null 2>&1 || useradd --system --home "$DATA" --shell /usr/sbin/nologin "$APP_USER";install -d -m0750 -o "$APP_USER" -g "$APP_USER" "$DATA";install -d -m0750 -o root -g "$APP_USER" "$CONF";if [ ! -f "$ENV" ];then umask 077;cat >"$ENV" <<EOT
APP_PORT=18765
PUBLIC_URL=https://135ercloud.grow-central.de
DATABASE_URL=sqlite:////var/lib/135er-growcentral-cloud/cloud.sqlite3
SERVER_SECRET=$(openssl rand -hex 32)
COOKIE_SECRET=$(openssl rand -hex 32)
ACCESS_TTL_SECONDS=900
REFRESH_TTL_SECONDS=2592000
PAIR_TTL_SECONDS=600
EOT
fi;chown root:"$APP_USER" "$ENV";chmod 0640 "$ENV";ok "Persistente Konfiguration"
step "Cloud-App prüfen"; runuser -u "$APP_USER" -- python3 -m py_compile /usr/lib/135er-growcentral-cloud/app.py && ok "Python-App OK" || { fail "Python-App fehlerhaft";finish; }
step "Dienst starten";systemctl daemon-reload;systemctl enable "$SERVICE" >/dev/null;systemctl restart "$SERVICE";sleep 2;systemctl is-active --quiet "$SERVICE" && ok "Service aktiv" || { fail "Service failed";journalctl -u "$SERVICE" -n40 --no-pager||true;finish; }
step "Lokalen Healthcheck prüfen";curl -fsS "http://127.0.0.1:$PORT/health" >/dev/null && ok "Backend lokal OK" || { fail "Healthcheck failed";finish; }
step "Subdomain/DNS prüfen";plesk bin subdomain --info "$DOMAIN" >/dev/null 2>&1 || plesk bin subdomain --create "135ercloud" -domain "$ROOT_DOMAIN" -ssl true >/dev/null;getent ahostsv4 "$DOMAIN" >/dev/null 2>&1 && ok "Subdomain + DNS OK" || warn "DNS noch nicht bereit"
step "TLS prüfen";if tls;then ok "TLS gültig";else E="$(plesk db -Ne "SELECT email FROM clients WHERE login='admin' LIMIT 1" 2>/dev/null||true)";if [ -n "$E" ] && plesk bin extension --exec letsencrypt cli.php -d "$DOMAIN" -m "$E";then plesk bin site -u "$DOMAIN" -certificate-name "Lets Encrypt $DOMAIN" >/dev/null 2>&1||true;sleep 1;tls&&ok "Let's Encrypt aktiv"||warn "TLS noch nicht bestätigt";else warn "TLS-Automatik fehlgeschlagen";fi;fi
step "Reverse Proxy einrichten";mkdir -p "$(dirname "$VHOST")";cat >"$VHOST" <<EOT
location ~ ^/.* {
 proxy_pass http://127.0.0.1:$PORT;
 proxy_http_version 1.1;
 proxy_set_header Host \$host;
 proxy_set_header X-Real-IP \$remote_addr;
 proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
 proxy_set_header X-Forwarded-Proto \$scheme;
 proxy_set_header Upgrade \$http_upgrade;
 proxy_set_header Connection "upgrade";
 proxy_read_timeout 180s;
 proxy_buffering off;
}
EOT
plesk sbin httpdmng --reconfigure-domain "$DOMAIN" >/dev/null && nginx -t >/dev/null 2>&1 && systemctl reload nginx && ok "Proxy aktiv" || { fail "Proxy-Konfiguration failed";finish; }
step "Öffentliche Abschlussprüfung";curl -fsS "https://$DOMAIN/health" >/dev/null 2>&1 && curl -fsS "https://$DOMAIN/.well-known/growcentral-cloud" >/dev/null 2>&1 && ok "Cloud öffentlich OK" || warn "Öffentliche Prüfung noch nicht vollständig"
finish
EOF
chmod 0755 "$PKG/usr/lib/135er-growcentral-cloud/setup.sh"

cat > "$PKG/DEBIAN/postinst" <<'EOF'
#!/bin/sh
set -e
[ "$1" != configure ] || /usr/lib/135er-growcentral-cloud/setup.sh
exit 0
EOF
chmod 0755 "$PKG/DEBIAN/postinst"

cat > "$PKG/DEBIAN/prerm" <<'EOF'
#!/bin/sh
set -e
[ "$1" != remove ] || systemctl stop 135er-growcentral-cloud.service 2>/dev/null || true
exit 0
EOF
chmod 0755 "$PKG/DEBIAN/prerm"

DEB="$TMP/135er-growcentral-cloud_${VERSION}_all.deb"
dpkg-deb --build --root-owner-group "$PKG" "$DEB" >/dev/null
dpkg-deb --info "$DEB" >/dev/null
ok "Paket $(basename "$DEB") gebaut"

step "[4/8] Signaturschlüssel erzeugen/verwenden"
mkdir -p "$GNUPGHOME";chmod 0700 "$GNUPGHOME"
if ! GNUPGHOME="$GNUPGHOME" gpg --batch --list-secret-keys "$KEY_NAME" >/dev/null 2>&1;then
 GNUPGHOME="$GNUPGHOME" gpg --batch --passphrase '' --quick-generate-key "$KEY_NAME" rsa3072 sign 5y
fi
ok "Repository-Signaturschlüssel bereit"

step "[5/8] Repository-Dateien publizieren"
mkdir -p "$REPO_ROOT/pool/main/1/135er-growcentral-cloud" "$REPO_ROOT/dists/stable/main/binary-amd64"
install -m0644 "$DEB" "$REPO_ROOT/pool/main/1/135er-growcentral-cloud/"
GNUPGHOME="$GNUPGHOME" gpg --batch --yes --armor --export-options export-minimal --export "$KEY_NAME" >"$REPO_ROOT/repo-key.asc"
cd "$REPO_ROOT"
apt-ftparchive packages pool >dists/stable/main/binary-amd64/Packages
gzip -9c dists/stable/main/binary-amd64/Packages >dists/stable/main/binary-amd64/Packages.gz
apt-ftparchive -o APT::FTPArchive::Release::Origin="135er GrowCentral" -o APT::FTPArchive::Release::Label="135er GrowCentral" -o APT::FTPArchive::Release::Suite="stable" -o APT::FTPArchive::Release::Codename="stable" -o APT::FTPArchive::Release::Architectures="amd64" -o APT::FTPArchive::Release::Components="main" release dists/stable >dists/stable/Release
GNUPGHOME="$GNUPGHOME" gpg --batch --yes --local-user "$KEY_NAME" --clearsign -o dists/stable/InRelease dists/stable/Release
GNUPGHOME="$GNUPGHOME" gpg --batch --yes --local-user "$KEY_NAME" -abs -o dists/stable/Release.gpg dists/stable/Release
chmod -R a+rX "$REPO_ROOT"
ok "Repository signiert"

step "[6/8] Lokalen Server als APT-Client registrieren"
install -d -m0755 /etc/apt/keyrings
install -m0644 "$REPO_ROOT/repo-key.asc" /etc/apt/keyrings/135er-growcentral.asc
cat >/etc/apt/sources.list.d/135er-growcentral.sources <<EOF
Types: deb
URIs: $REPO_URL
Suites: stable
Components: main
Architectures: amd64
Signed-By: /etc/apt/keyrings/135er-growcentral.asc
EOF
ok "Deb822-Quelle + Signed-By eingerichtet"

step "[7/8] Repository über HTTPS prüfen"
if curl -fsS "$REPO_URL/dists/stable/InRelease" >/dev/null;then ok "HTTPS Repository erreichbar";else warn "Dateien liegen bereit, HTTPS-Pfad noch nicht erreichbar";fi

step "[8/8] APT-Test"
if apt-get update;then
 apt-cache policy 135er-growcentral-cloud | sed -n '1,12p'
 ok "APT erkennt 135er-growcentral-cloud"
else
 warn "apt update meldet noch einen Fehler; Webpfad/Cache prüfen"
fi

echo
echo "=============================================================================="
echo -e "  REPOSITORY STATUS: ${G}OK${R}"
echo "=============================================================================="
echo "Installation künftig:"
echo "  apt install 135er-growcentral-cloud"
echo "Updates künftig:"
echo "  apt update && apt upgrade"
