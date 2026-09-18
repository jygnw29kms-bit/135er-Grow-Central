#!/usr/bin/env bash
set -Eeuo pipefail

ROOT_DOMAIN="${ROOT_DOMAIN:-grow-central.de}"
REPO_HOST="${REPO_HOST:-repo.grow-central.de}"
REPO_SUB="${REPO_HOST%.$ROOT_DOMAIN}"
REPO_URL="https://${REPO_HOST}/apt"
DOCROOT_REL="/repo.grow-central.de"
DOCROOT="/var/www/vhosts/${ROOT_DOMAIN}${DOCROOT_REL}"
APT_ROOT="${DOCROOT}/apt"
KEY_HOME="/root/.gnupg-135er-growcentral-repo"
KEY_EMAIL="${KEY_EMAIL:-repo@grow-central.de}"
PKG_NAME="135er-growcentral-cloud"
PKG_VERSION="${PKG_VERSION:-6.1.0}"
INSTALLER_URL="${INSTALLER_URL:-https://raw.githubusercontent.com/jygnw29kms-bit/135er-Grow-Central/master/scripts/install-135ercloud-v6.sh}"

C_RESET='\033[0m'; C_GREEN='\033[1;32m'; C_YELLOW='\033[1;33m'; C_RED='\033[1;31m'; C_CYAN='\033[1;36m'
TOTAL=10; STEP=0; WARN=0; FAIL=0
begin(){ STEP=$((STEP+1)); printf "\n[%02d/%02d] ${C_CYAN}%s${C_RESET}\n" "$STEP" "$TOTAL" "$*"; }
ok(){ printf "       ${C_GREEN}✓ OK${C_RESET}      %s\n" "$*"; }
warning(){ WARN=$((WARN+1)); printf "       ${C_YELLOW}! WARN${C_RESET}    %s\n" "$*"; }
failed(){ FAIL=1; printf "       ${C_RED}✗ FAILED${C_RESET}  %s\n" "$*" >&2; }
finish(){
  echo
  echo "=============================================================================="
  echo "  135er GrowCentral APT Repository - STATUS"
  echo "=============================================================================="
  echo "  Repository : $REPO_URL"
  echo "  Paket      : $PKG_NAME $PKG_VERSION"
  echo "  Warnungen  : $WARN"
  if [[ "$FAIL" -eq 1 ]]; then echo -e "  STATUS     : ${C_RED}FAILED${C_RESET}"; exit 1
  elif [[ "$WARN" -gt 0 ]]; then echo -e "  STATUS     : ${C_YELLOW}OK MIT WARNUNGEN${C_RESET}"
  else echo -e "  STATUS     : ${C_GREEN}OK${C_RESET}"; fi
  echo "=============================================================================="
}
[[ $EUID -eq 0 ]] || { echo "Als root ausführen."; exit 1; }

echo
echo "=============================================================================="
echo "  135er GrowCentral - APT Repository Setup"
echo "=============================================================================="
echo "  Host : $REPO_HOST"
echo "  URL  : $REPO_URL"
echo "=============================================================================="

begin "Plesk und Root-Domain prüfen"
command -v plesk >/dev/null 2>&1 && plesk bin domain --info "$ROOT_DOMAIN" >/dev/null 2>&1 \
  && ok "Plesk + $ROOT_DOMAIN vorhanden" || { failed "Plesk/Domain fehlt"; finish; }

begin "Repo-Abhängigkeiten installieren"
export DEBIAN_FRONTEND=noninteractive
apt-get update -y >/dev/null
apt-get install -y --no-install-recommends apt-utils dpkg-dev gnupg ca-certificates curl wget openssl >/dev/null \
  && ok "apt-ftparchive, dpkg-deb und GPG verfügbar" || { failed "Pakete fehlen"; finish; }

begin "Plesk-Subdomain $REPO_HOST erstellen"
if plesk bin subdomain --info "$REPO_HOST" >/dev/null 2>&1; then
  ok "Subdomain existiert bereits"
else
  plesk bin subdomain --create "$REPO_SUB" -domain "$ROOT_DOMAIN" \
    -www-root "$DOCROOT_REL" -php false -ssi false -cgi false -fastcgi false -ssl true >/dev/null \
    && ok "Subdomain mit separatem Document-Root erstellt" \
    || { failed "Subdomain konnte nicht erstellt werden"; finish; }
fi

begin "DNS A-Record prüfen/anlegen"
SERVER_IP="$(hostname -I | awk '{print $1}')"
if getent ahostsv4 "$REPO_HOST" >/dev/null 2>&1; then
  ok "$REPO_HOST ist bereits auflösbar"
else
  set +e
  plesk bin dns --add "$ROOT_DOMAIN" -a "$REPO_SUB" -ip "$SERVER_IP" >/dev/null 2>&1
  DNS_RC=$?
  set -e
  if [[ "$DNS_RC" -eq 0 || "$DNS_RC" -eq 2 ]]; then
    warning "Plesk-DNS-Eintrag gesetzt/war vorhanden; externe DNS-Propagation kann dauern"
  else
    warning "Plesk verwaltet DNS möglicherweise nicht extern; A-Record $REPO_SUB -> $SERVER_IP manuell prüfen"
  fi
fi

begin "Repository-Verzeichnis vorbereiten"
install -d -m 0755 "$APT_ROOT/pool/main/g/growcentral" \
  "$APT_ROOT/dists/stable/main/binary-amd64" \
  "$APT_ROOT/dists/stable/main/binary-arm64" \
  "$APT_ROOT/dists/stable/main/binary-armhf"
ok "$APT_ROOT vorbereitet"

begin "Signaturschlüssel erstellen/verwenden"
install -d -m 0700 "$KEY_HOME"
export GNUPGHOME="$KEY_HOME"
if ! gpg --batch --list-secret-keys "$KEY_EMAIL" >/dev/null 2>&1; then
  gpg --batch --passphrase '' --quick-gen-key \
    "135er GrowCentral APT Repository <$KEY_EMAIL>" ed25519 sign 3y >/dev/null
fi
FPR="$(gpg --batch --with-colons --list-secret-keys "$KEY_EMAIL" | awk -F: '$1=="fpr"{print $10;exit}')"
[[ -n "$FPR" ]] || { failed "GPG-Fingerprint fehlt"; finish; }
gpg --batch --yes --output "$APT_ROOT/growcentral-archive-keyring.gpg" --export "$FPR"
gpg --batch --yes --armor --output "$APT_ROOT/growcentral-archive-keyring.asc" --export "$FPR"
ok "Repository-Schlüssel: $FPR"

begin "V6-Installer laden und Debian-Paket bauen"
BUILD="$(mktemp -d)"
trap 'rm -rf "$BUILD"' EXIT
wget -qO "$BUILD/install-135ercloud-v6.sh" "$INSTALLER_URL"
chmod 0755 "$BUILD/install-135ercloud-v6.sh"

PKGDIR="$BUILD/pkg"
install -d "$PKGDIR/DEBIAN" "$PKGDIR/usr/lib/135er-growcentral-cloud" "$PKGDIR/usr/sbin"
install -m 0755 "$BUILD/install-135ercloud-v6.sh" "$PKGDIR/usr/lib/135er-growcentral-cloud/install-135ercloud-v6.sh"

cat > "$PKGDIR/DEBIAN/control" <<EOF
Package: $PKG_NAME
Version: $PKG_VERSION
Section: admin
Priority: optional
Architecture: all
Maintainer: 135er GrowCentral <repo@grow-central.de>
Depends: ca-certificates, curl, wget, openssl, openssh-server, sqlite3, python3, python3-venv, python3-pip, iproute2, util-linux, gnupg
Description: 135er GrowCentral Cloud Server
 Plesk-safe GrowCentral Cloud service with account/device pairing,
 Ed25519 device identity, HTTPS/WSS reverse proxy and remote relay.
EOF

cat > "$PKGDIR/DEBIAN/postinst" <<'EOF'
#!/usr/bin/env bash
set -e
/usr/lib/135er-growcentral-cloud/install-135ercloud-v6.sh --package-mode
EOF
chmod 0755 "$PKGDIR/DEBIAN/postinst"

cat > "$PKGDIR/usr/sbin/135ercloud-setup" <<'EOF'
#!/usr/bin/env bash
exec /usr/lib/135er-growcentral-cloud/install-135ercloud-v6.sh "$@"
EOF
chmod 0755 "$PKGDIR/usr/sbin/135ercloud-setup"

DEB="$APT_ROOT/pool/main/g/growcentral/${PKG_NAME}_${PKG_VERSION}_all.deb"
dpkg-deb --build --root-owner-group "$PKGDIR" "$DEB" >/dev/null
ok "Paket gebaut: $(basename "$DEB")"

begin "APT-Indizes erzeugen"
cd "$APT_ROOT"
apt-ftparchive packages pool/main > "$BUILD/Packages"
for arch in amd64 arm64 armhf; do
  cp "$BUILD/Packages" "dists/stable/main/binary-${arch}/Packages"
  gzip -9fk "dists/stable/main/binary-${arch}/Packages"
done
apt-ftparchive \
  -o APT::FTPArchive::Release::Origin="135er GrowCentral" \
  -o APT::FTPArchive::Release::Label="135er GrowCentral" \
  -o APT::FTPArchive::Release::Suite="stable" \
  -o APT::FTPArchive::Release::Codename="stable" \
  -o APT::FTPArchive::Release::Architectures="amd64 arm64 armhf" \
  -o APT::FTPArchive::Release::Components="main" \
  release dists/stable > dists/stable/Release
gpg --batch --yes --local-user "$FPR" --clearsign -o dists/stable/InRelease dists/stable/Release
gpg --batch --yes --local-user "$FPR" -abs -o dists/stable/Release.gpg dists/stable/Release
ok "Packages, Release, InRelease und Release.gpg erzeugt"

begin "TLS für $REPO_HOST einrichten"
ADMIN_EMAIL="$(plesk bin admin --info 2>/dev/null | awk -F': *' '/^Email:/ {print $2;exit}' || true)"
[[ -n "$ADMIN_EMAIL" ]] || ADMIN_EMAIL="$(plesk db -Ne "SELECT email FROM clients WHERE login='admin' LIMIT 1" 2>/dev/null || true)"
if [[ -n "$ADMIN_EMAIL" ]] && plesk bin extension --exec letsencrypt cli.php -d "$REPO_HOST" -m "$ADMIN_EMAIL" >/dev/null 2>&1; then
  CERT="Lets Encrypt ${REPO_HOST}"
  plesk bin site -u "$REPO_HOST" -certificate-name "$CERT" >/dev/null 2>&1 || true
  plesk sbin httpdmng --reconfigure-domain "$REPO_HOST" >/dev/null 2>&1 || true
  systemctl reload nginx >/dev/null 2>&1 || true
  ok "Let's Encrypt angefordert/aktiviert"
else
  warning "TLS konnte noch nicht automatisch ausgestellt werden (oft DNS-Propagation)"
fi

begin "Repository öffentlich prüfen"
if curl -fsS --connect-timeout 10 "$REPO_URL/dists/stable/InRelease" >/dev/null 2>&1 \
   && curl -fsS --connect-timeout 10 "$REPO_URL/growcentral-archive-keyring.gpg" >/dev/null 2>&1; then
  ok "APT-Repository öffentlich erreichbar"
else
  warning "Repository lokal erstellt, öffentlich ggf. erst nach DNS/TLS-Propagation erreichbar"
fi

finish
