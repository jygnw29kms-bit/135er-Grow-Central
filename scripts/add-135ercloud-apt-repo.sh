#!/usr/bin/env bash
set -Eeuo pipefail

REPO="https://repo.grow-central.de/apt"
KEY="/usr/share/keyrings/135er-growcentral-archive-keyring.gpg"
SOURCE="/etc/apt/sources.list.d/135er-growcentral.sources"
APT_DIR="/etc/apt"
BACKUP_ROOT="/var/backups/135er-growcentral-apt"
MATCH_RE='repo\.dezender\.de/apt|135er[-_ ]?(growcentral|cloud)|growcentral-archive-keyring'

[[ $EUID -eq 0 ]] || { echo "Als root ausführen."; exit 1; }
for cmd in awk cmp cp curl find install mktemp; do
  command -v "$cmd" >/dev/null 2>&1 || { echo "Fehlendes Werkzeug: $cmd" >&2; exit 1; }
done

BACKUP_DIR="$BACKUP_ROOT/$(date -u +%Y%m%dT%H%M%SZ)"
BACKUP_CREATED=0

backup_file() {
  local file="$1" target
  target="$BACKUP_DIR$(dirname "$file")"
  mkdir -p "$target"
  cp -a "$file" "$target/"
  BACKUP_CREATED=1
}

clean_list_file() {
  local file="$1" tmp
  grep -Eqi "$MATCH_RE" "$file" || return 0
  tmp="$(mktemp "${file}.growcentral.XXXXXX")"
  awk -v re="$MATCH_RE" 'tolower($0) !~ re { print }' "$file" > "$tmp"
  if cmp -s "$file" "$tmp"; then
    rm -f "$tmp"
    return 0
  fi
  backup_file "$file"
  if [[ -s "$tmp" ]]; then
    chmod --reference="$file" "$tmp" 2>/dev/null || chmod 0644 "$tmp"
    chown --reference="$file" "$tmp" 2>/dev/null || true
    mv "$tmp" "$file"
  else
    rm -f "$tmp" "$file"
  fi
  echo "      bereinigt: $file"
}

clean_sources_file() {
  local file="$1" tmp
  grep -Eqi "$MATCH_RE" "$file" || return 0
  tmp="$(mktemp "${file}.growcentral.XXXXXX")"
  awk -v re="$MATCH_RE" 'BEGIN { RS=""; ORS="\n\n" } tolower($0) !~ re { print }' "$file" > "$tmp"
  if cmp -s "$file" "$tmp"; then
    rm -f "$tmp"
    return 0
  fi
  backup_file "$file"
  if grep -q '[^[:space:]]' "$tmp"; then
    chmod --reference="$file" "$tmp" 2>/dev/null || chmod 0644 "$tmp"
    chown --reference="$file" "$tmp" 2>/dev/null || true
    mv "$tmp" "$file"
  else
    rm -f "$tmp" "$file"
  fi
  echo "      bereinigt: $file"
}

echo "[1/5] Alte GrowCentral-APT-Quellen prüfen"
mkdir -p "$APT_DIR/sources.list.d"
if [[ -f "$APT_DIR/sources.list" ]]; then
  clean_list_file "$APT_DIR/sources.list"
fi
while IFS= read -r -d '' file; do
  [[ "$file" == "$SOURCE" ]] && continue
  case "$file" in
    *.sources) clean_sources_file "$file" ;;
    *.list) clean_list_file "$file" ;;
  esac
done < <(find "$APT_DIR/sources.list.d" -maxdepth 1 -type f \( -name '*.list' -o -name '*.sources' \) -print0)

# Die kanonische Datei selbst wird ebenfalls gesichert und neu erzeugt. So
# verschwinden auch dort Altstände mit abweichendem Signed-By zuverlässig.
if [[ -f "$SOURCE" ]]; then
  backup_file "$SOURCE"
  rm -f "$SOURCE"
  echo "      ersetzt: $SOURCE"
fi
if [[ "$BACKUP_CREATED" -eq 1 ]]; then
  chmod -R go-rwx "$BACKUP_DIR"
  echo "      Backup: $BACKUP_DIR"
else
  rmdir "$BACKUP_DIR" 2>/dev/null || true
  echo "      keine Altquellen gefunden"
fi

echo "[2/5] Repository-Schlüssel laden"
curl -fsSL "$REPO/growcentral-archive-keyring.gpg" -o "${KEY}.tmp"
install -m 0644 "${KEY}.tmp" "$KEY"
rm -f "${KEY}.tmp"
echo "      OK"

echo "[3/5] Kanonische Debian-APT-Quelle eintragen"
cat > "$SOURCE" <<EOF
Types: deb
URIs: $REPO
Suites: stable
Components: main
Signed-By: $KEY
EOF
chmod 0644 "$SOURCE"
echo "      OK"

echo "[4/5] Paketlisten aktualisieren"
apt-get update
echo "      OK"

echo "[5/5] 135er GrowCentral Cloud installieren/aktualisieren"
apt-get install -y 135er-growcentral-cloud
echo "      OK"
