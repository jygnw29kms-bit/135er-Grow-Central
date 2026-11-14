#!/usr/bin/env bash
set -Eeuo pipefail
# GC-OS Final Master deploy. One canonical UI, one responsive PWA.
ROOT=/opt/135er-grow-central
WEB="$ROOT/web"
RAW="https://raw.githubusercontent.com/jygnw29kms-bit/135er-Grow-Central/master"
WEB_FILES=(gc-final.html gc-final.css gc-final.js gc-worker.js gc-manifest.webmanifest)
APP_FILES=(rooms.py)
[[ ${EUID} -eq 0 ]] || { echo "sudo required" >&2; exit 1; }
TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT
for f in "${WEB_FILES[@]}"; do
  curl -fLsS --retry 3 --connect-timeout 10 "$RAW/web/$f" -o "$TMP/$f"
  [[ -s "$TMP/$f" ]] || exit 2
done
for f in "${APP_FILES[@]}"; do
  curl -fLsS --retry 3 --connect-timeout 10 "$RAW/app/$f" -o "$TMP/$f"
  [[ -s "$TMP/$f" ]] || exit 2
done
grep -q 'class="master-columns"' "$TMP/gc-final.html"
grep -q 'id="growbook"' "$TMP/gc-final.html"
grep -q 'id="cameraSettingsPanel"' "$TMP/gc-final.html"
grep -q 'async function loadJournal' "$TMP/gc-final.js"
grep -q 'function controlMarkup' "$TMP/gc-final.js"
grep -q 'master-columns' "$TMP/gc-final.css"
python3 -m py_compile "$TMP/rooms.py"
# Preserve full-resolution product images locally. Do not redistribute them via GitHub.
if [[ ! -s "$WEB/mars-fc3000-hires.jpg" ]]; then
  curl -fLsS --retry 3 --max-time 45 'https://cdn.shopify.com/s/files/1/0555/7266/0422/files/fc3000_smart.jpg?v=1684813843' -o "$TMP/mars-fc3000-hires.jpg"
fi
if [[ ! -s "$WEB/mars-df150m-hires.jpg" ]]; then
  curl -fLsS --retry 3 --max-time 45 'https://marshydroled.ca/cdn/shop/products/2_a2ddeabd-1bab-4918-911f-7d11e4b96442.jpg?v=1722485403' -o "$TMP/fan-source.jpg"
  ffmpeg -y -hide_banner -loglevel error -i "$TMP/fan-source.jpg" -vf 'crop=1460:560:20:475' -q:v 2 -frames:v 1 "$TMP/mars-df150m-hires.jpg"
fi
if [[ ! -s "$WEB/gc-hero-leaf.jpg" ]]; then
  curl -fLsS --retry 3 --max-time 45 'https://images.unsplash.com/photo-1496991541240-6b274c090423?w=2200&q=90&fit=crop' -o "$TMP/gc-hero-leaf.jpg"
fi
STAMP="$(date +%Y%m%d-%H%M%S)"
BACKUP="/var/lib/135er-grow-central/gui-source-archive/deploy-$STAMP"
install -d -m 0700 "$BACKUP"
for f in "${WEB_FILES[@]}"; do [[ ! -f "$WEB/$f" ]] || cp -a "$WEB/$f" "$BACKUP/$f"; done
for f in "${APP_FILES[@]}"; do [[ ! -f "$ROOT/app/$f" ]] || cp -a "$ROOT/app/$f" "$BACKUP/$f"; done
rollback(){
 echo 'Deploy failed. Restoring previous GC-OS files.' >&2
 for f in "${WEB_FILES[@]}"; do [[ ! -f "$BACKUP/$f" ]] || cp -a "$BACKUP/$f" "$WEB/$f"; done
 for f in "${APP_FILES[@]}"; do [[ ! -f "$BACKUP/$f" ]] || cp -a "$BACKUP/$f" "$ROOT/app/$f"; done
 systemctl restart 135er-grow-central.service || true
}
trap 'rollback; rm -rf "$TMP"' ERR
for f in "${WEB_FILES[@]}"; do install -m 0644 "$TMP/$f" "$WEB/$f"; done
for f in "${APP_FILES[@]}"; do install -m 0644 "$TMP/$f" "$ROOT/app/$f"; done
for img in mars-fc3000-hires.jpg mars-df150m-hires.jpg gc-hero-leaf.jpg; do
 [[ ! -s "$TMP/$img" ]] || install -m 0644 "$TMP/$img" "$WEB/$img"
done
# Render transparent presentation assets from full-resolution original photos.
ffmpeg -y -hide_banner -loglevel error -i "$WEB/mars-fc3000-hires.jpg" -vf 'format=rgba,colorkey=0xFFFFFF:0.095:0.065' -frames:v 1 -pix_fmt rgba "$WEB/mars-fc3000-transparent.png"
systemctl restart 135er-grow-central.service
systemctl is-active --quiet 135er-grow-central.service
curl -fsS --max-time 7 http://127.0.0.1:8080/static/gc-final.js >/dev/null
trap 'rm -rf "$TMP"' EXIT
echo "FINAL_MASTER_DEPLOYED /ui"
