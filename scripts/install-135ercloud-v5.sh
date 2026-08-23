#!/usr/bin/env bash
set -Eeuo pipefail
REPO="https://dezender.de/apt/135er-growcentral"
KEY="/etc/apt/keyrings/135er-growcentral.asc"
SOURCE="/etc/apt/sources.list.d/135er-growcentral.sources"
FALLBACK="https://raw.githubusercontent.com/jygnw29kms-bit/135er-Grow-Central/master/scripts/install-135ercloud-v4.sh"

G='\033[1;32m';Y='\033[1;33m';R='\033[0m';C='\033[1;36m';X='\033[1;31m'
echo
echo "=============================================================================="
echo "  135er GrowCentral Cloud V5 - Installer"
echo "=============================================================================="

if curl -fsS --connect-timeout 8 "$REPO/dists/stable/InRelease" >/dev/null 2>&1;then
 echo -e "${C}[1/4] Signiertes APT-Repository erkannt${R}"
 install -d -m0755 /etc/apt/keyrings
 curl -fsSL "$REPO/repo-key.asc" -o "$KEY"
 chmod 0644 "$KEY"
 cat >"$SOURCE" <<EOF
Types: deb
URIs: $REPO
Suites: stable
Components: main
Architectures: amd64
Signed-By: $KEY
EOF
 echo -e "      ${G}✓ OK${R}"
 echo -e "${C}[2/4] APT-Metadaten aktualisieren${R}"
 apt-get update
 echo -e "      ${G}✓ OK${R}"
 echo -e "${C}[3/4] GrowCentral installieren/aktualisieren${R}"
 apt-get install -y 135er-growcentral-cloud
 echo -e "      ${G}✓ OK${R}"
 echo -e "${C}[4/4] Status prüfen${R}"
 systemctl is-active --quiet 135er-growcentral-cloud && curl -fsS https://135ercloud.dezender.de/health >/dev/null
 echo -e "      ${G}✓ OK${R}"
 echo
 echo -e "GESAMTSTATUS: ${G}OK${R} (APT)"
else
 echo -e "${Y}! APT-Repository ist noch nicht erreichbar.${R}"
 echo "  Einmaliger Fallback auf den bisherigen Installer."
 TMP="$(mktemp)";trap 'rm -f "$TMP"' EXIT
 curl -fsSL "$FALLBACK" -o "$TMP"
 chmod +x "$TMP"
 "$TMP"
 echo
 echo -e "${Y}Hinweis:${R} Sobald das APT-Repo eingerichtet ist, übernimmt APT zukünftige Updates."
fi
