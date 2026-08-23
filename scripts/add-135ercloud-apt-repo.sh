#!/usr/bin/env bash
set -Eeuo pipefail
REPO="https://repo.dezender.de/apt"
KEY="/usr/share/keyrings/135er-growcentral-archive-keyring.gpg"
SOURCE="/etc/apt/sources.list.d/135er-growcentral.sources"
[[ $EUID -eq 0 ]] || { echo "Als root ausführen."; exit 1; }

echo "[1/4] Repository-Schlüssel laden"
curl -fsSL "$REPO/growcentral-archive-keyring.gpg" -o "${KEY}.tmp"
install -m 0644 "${KEY}.tmp" "$KEY"
rm -f "${KEY}.tmp"
echo "      OK"

echo "[2/4] Debian APT-Quelle eintragen"
cat > "$SOURCE" <<EOF
Types: deb
URIs: $REPO
Suites: stable
Components: main
Signed-By: $KEY
EOF
echo "      OK"

echo "[3/4] Paketlisten aktualisieren"
apt-get update
echo "      OK"

echo "[4/4] 135er GrowCentral Cloud installieren/aktualisieren"
apt-get install -y 135er-growcentral-cloud
echo "      OK"
