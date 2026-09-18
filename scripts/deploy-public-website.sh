#!/usr/bin/env bash
set -euo pipefail

SOURCE="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/../website" && pwd)"
TARGET="${1:-/var/www/vhosts/grow-central.de/httpdocs}"
FILES=(
  index.html styles.css impressum.html datenschutz.html
  assets/brand/135er-grow-central-lockup-v0.9.png
  assets/brand/135er-grow-central-mark.png
  assets/gui/local-desktop-v0.9.png
)

# Validate the complete public allowlist before changing the destination.
for file in "${FILES[@]}"; do
  [[ -f "$SOURCE/$file" ]] || { echo "Missing public file: $file" >&2; exit 1; }
done
for file in "${FILES[@]}"; do
  install -D -m 0644 "$SOURCE/$file" "$TARGET/$file"
done
printf 'Public website deployed to %s\n' "$TARGET"
