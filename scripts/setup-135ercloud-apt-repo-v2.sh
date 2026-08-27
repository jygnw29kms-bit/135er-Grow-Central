#!/usr/bin/env bash
set -Eeuo pipefail

ROOT_DOMAIN="${ROOT_DOMAIN:-dezender.de}"
REPO_HOST="${REPO_HOST:-repo.dezender.de}"
REPO_URL="https://${REPO_HOST}/apt"
DOCROOT="${DOCROOT:-/var/www/vhosts/${ROOT_DOMAIN}/repo.dezender.de}"
APT_ROOT="${APT_ROOT:-${DOCROOT}/apt}"
KEY_HOME="${KEY_HOME:-/root/.gnupg-135er-growcentral-repo}"
KEY_EMAIL="${KEY_EMAIL:-repo@dezender.de}"
PKG_NAME="135er-growcentral-cloud"
PKG_VERSION="${PKG_VERSION:-7.0.0}"
RAW="https://raw.githubusercontent.com/jygnw29kms-bit/135er-Grow-Central/master"

ok(){ printf '\033[1;32m[OK]\033[0m %s\n' "$*"; }
log(){ printf '\033[1;36m[APT V7]\033[0m %s\n' "$*"; }
warn(){ printf '\033[1;33m[WARN]\033[0m %s\n' "$*"; }
die(){ printf '\033[1;31m[FEHLER]\033[0m %s\n' "$*" >&2; exit 1; }
[[ $EUID -eq 0 ]] || die "Als root ausführen."

export DEBIAN_FRONTEND=noninteractive
apt-get update -y >/dev/null
apt-get install -y --no-install-recommends apt-utils dpkg-dev gnupg ca-certificates curl wget openssl >/dev/null

# Repository hosting is currently on the project Plesk server. This requirement
# applies only to the REPOSITORY PUBLISHER, never to installed Cloud V7 servers.
command -v plesk >/dev/null 2>&1 || die "Repository-Publisher erwartet den bestehenden Plesk-Host."
plesk bin domain --info "$ROOT_DOMAIN" >/dev/null 2>&1 || die "Plesk-Domain $ROOT_DOMAIN fehlt."

install -d -m 0755 \
  "$APT_ROOT/pool/main/g/growcentral" \
  "$APT_ROOT/dists/stable/main/binary-amd64" \
  "$APT_ROOT/dists/stable/main/binary-arm64" \
  "$APT_ROOT/dists/stable/main/binary-armhf"

install -d -m 0700 "$KEY_HOME"
export GNUPGHOME="$KEY_HOME"
if ! gpg --batch --list-secret-keys "$KEY_EMAIL" >/dev/null 2>&1; then
  gpg --batch --passphrase '' --quick-gen-key "135er GrowCentral APT Repository <$KEY_EMAIL>" ed25519 sign 3y >/dev/null
fi
FPR="$(gpg --batch --with-colons --list-secret-keys "$KEY_EMAIL" | awk -F: '$1=="fpr"{print $10;exit}')"
[[ -n "$FPR" ]] || die "GPG-Fingerprint fehlt"
gpg --batch --yes --output "$APT_ROOT/growcentral-archive-keyring.gpg" --export "$FPR"
gpg --batch --yes --armor --output "$APT_ROOT/growcentral-archive-keyring.asc" --export "$FPR"

BUILD="$(mktemp -d)"
trap 'rm -rf "$BUILD"' EXIT
PKG="$BUILD/pkg"
install -d "$PKG/DEBIAN" "$PKG/usr/lib/$PKG_NAME/v7" "$PKG/usr/sbin"

fetch(){ curl -fsSL "$1" -o "$2"; }
fetch "$RAW/scripts/install-135ercloud-v7.sh" "$PKG/usr/lib/$PKG_NAME/install-135ercloud-v7.sh"
fetch "$RAW/scripts/install-135ercloud-v6.sh" "$PKG/usr/lib/$PKG_NAME/install-135ercloud-v6.sh"
fetch "$RAW/scripts/bootstrap-standalone-cloud-core.sh" "$PKG/usr/lib/$PKG_NAME/bootstrap-standalone-cloud-core.sh"
fetch "$RAW/scripts/configure-cloud-admin-mode.sh" "$PKG/usr/lib/$PKG_NAME/configure-cloud-admin-mode.sh"
fetch "$RAW/cloud/v7/admin_app.py" "$PKG/usr/lib/$PKG_NAME/v7/admin_app.py"
chmod 0755 "$PKG/usr/lib/$PKG_NAME/"*.sh
chmod 0644 "$PKG/usr/lib/$PKG_NAME/v7/admin_app.py"

cat > "$PKG/DEBIAN/control" <<EOF
Package: $PKG_NAME
Version: $PKG_VERSION
Section: admin
Priority: optional
Architecture: all
Maintainer: 135er GrowCentral <repo@dezender.de>
Depends: ca-certificates, curl, wget, openssl, openssh-server, sqlite3, python3, python3-venv, python3-pip, iproute2, util-linux, gnupg
Suggests: nginx, certbot, python3-certbot-nginx
Description: 135er Grow Central Cloud Server V7
 Upgrade-safe Grow Central cloud server with V6-compatible account/device core,
 central device entitlements and Plesk or standalone administration.
EOF

cat > "$PKG/DEBIAN/preinst" <<'EOF'
#!/usr/bin/env bash
set -e
# Never delete application data in maintainer scripts. V7 installer creates an
# online DB/config backup before schema changes.
exit 0
EOF
chmod 0755 "$PKG/DEBIAN/preinst"

cat > "$PKG/DEBIAN/postinst" <<'EOF'
#!/usr/bin/env bash
set -e
/usr/lib/135er-growcentral-cloud/install-135ercloud-v7.sh --package-mode
EOF
chmod 0755 "$PKG/DEBIAN/postinst"

cat > "$PKG/DEBIAN/prerm" <<'EOF'
#!/usr/bin/env bash
set -e
# Upgrades must keep services/data. Only stop admin sidecar on actual removal.
if [[ "${1:-}" == remove ]]; then
  systemctl stop 135er-growcentral-cloud-admin.service >/dev/null 2>&1 || true
fi
EOF
chmod 0755 "$PKG/DEBIAN/prerm"

cat > "$PKG/DEBIAN/postrm" <<'EOF'
#!/usr/bin/env bash
set -e
# Deliberately preserve /etc/135er-growcentral-cloud and /var/lib/... even on
# package removal. Explicit purge of user data requires a separate admin action.
exit 0
EOF
chmod 0755 "$PKG/DEBIAN/postrm"

cat > "$PKG/usr/sbin/135ercloud-setup" <<'EOF'
#!/usr/bin/env bash
exec /usr/lib/135er-growcentral-cloud/install-135ercloud-v7.sh "$@"
EOF
cat > "$PKG/usr/sbin/135ercloud-admin-mode" <<'EOF'
#!/usr/bin/env bash
exec /usr/lib/135er-growcentral-cloud/configure-cloud-admin-mode.sh "$@"
EOF
chmod 0755 "$PKG/usr/sbin/135ercloud-setup" "$PKG/usr/sbin/135ercloud-admin-mode"

# Static validation before publishing.
bash -n "$PKG/usr/lib/$PKG_NAME/install-135ercloud-v7.sh"
bash -n "$PKG/usr/lib/$PKG_NAME/bootstrap-standalone-cloud-core.sh"
bash -n "$PKG/usr/lib/$PKG_NAME/configure-cloud-admin-mode.sh"
python3 -m py_compile "$PKG/usr/lib/$PKG_NAME/v7/admin_app.py"

DEB="$APT_ROOT/pool/main/g/growcentral/${PKG_NAME}_${PKG_VERSION}_all.deb"
dpkg-deb --build --root-owner-group "$PKG" "$DEB" >/dev/null
ok "Paket gebaut: $DEB"

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

log "Prüfe veröffentlichte Paketmetadaten"
apt-cache show "$DEB" >/dev/null 2>&1 || dpkg-deb -I "$DEB" >/dev/null
sha256sum "$DEB" > "$DEB.sha256"
ok "V7 APT-Repository aktualisiert: $REPO_URL"
echo "Installierte Instanzen aktualisieren anschließend mit: apt update && apt upgrade"
