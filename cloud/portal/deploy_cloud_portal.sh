#!/usr/bin/env bash
# Install the existing Grow Central cloud portal and exact Final Master cloud copy.
# Static assets only; does not modify Plesk TLS, nginx, account DB, or device agent.
set -Eeuo pipefail
umask 022
root=/var/www/vhosts/grow-central.de/135ercloud.grow-central.de
work=$(mktemp -d /tmp/gc-cloud-deploy.XXXXXXXX)
trap 'rm -rf "$work"' EXIT
git clone -q --depth 1 --branch master https://github.com/jygnw29kms-bit/135er-Grow-Central.git "$work/repo"
repo="$work/repo"
stage="$work/web"
mkdir -p "$stage/static"
test -s "$repo/cloud/portal/index.html"
test -s "$repo/cloud/portal/cloud-portal.js"
test -s "$repo/cloud/portal/cloud-master.html"
node --check "$repo/cloud/portal/cloud-portal.js"
node --check "$repo/cloud/portal/cloud-master-bridge.js"
node --check "$repo/cloud/portal/gc-final-cloud.js"
node --check "$repo/cloud/portal/growbook-plants-wiki.js"
node --check "$repo/cloud/portal/climate-stage.js"
node --check "$repo/cloud/portal/tent-growing-wiki.js"
node --check "$repo/cloud/portal/room-setup.js"
cp "$repo/cloud/portal/index.html" "$stage/index.html"
cp "$repo/cloud/portal/cloud-master.html" "$stage/cloud-master.html"
cp "$repo/cloud/portal/cloud-portal.js" "$stage/cloud-portal.js"
cp "$repo/cloud/portal/cloud-master-bridge.js" "$stage/static/cloud-master-bridge.js"
cp "$repo/cloud/portal/gc-final-cloud.js" "$stage/static/gc-final.js"
cp "$repo/cloud/portal/gc-final-cloud.css" "$stage/static/gc-final.css"
cp "$repo/cloud/portal/growbook-plants-wiki.js" "$stage/static/growbook-plants-wiki.js"
cp "$repo/cloud/portal/growbook-plants-wiki.css" "$stage/static/growbook-plants-wiki.css"
cp "$repo/cloud/portal/climate-stage.js" "$stage/static/climate-stage.js"
cp "$repo/cloud/portal/climate-stage.css" "$stage/static/climate-stage.css"
cp "$repo/cloud/portal/tent-growing-wiki.js" "$stage/static/tent-growing-wiki.js"
cp "$repo/cloud/portal/tent-growing-wiki.css" "$stage/static/tent-growing-wiki.css"
cp "$repo/cloud/portal/room-setup.js" "$stage/static/room-setup.js"
cp "$repo/cloud/portal/room-setup.css" "$stage/static/room-setup.css"
for f in brand-logo.png brand-mark.png gc-icon-192.png gc-icon-512.png gc-manifest.webmanifest soil-sensor-reference.jpg; do
 cp "$repo/web/$f" "$stage/static/$f"
done
cp "$repo/web/brand-logo.png" "$stage/brand-logo.png"
cp "$repo/web/brand-mark.png" "$stage/brand-mark.png"
cp "$repo/web/master-grow-hero.jpg" "$stage/master-grow-hero.jpg"
for name in mars-hydro-fc3000.webp mars-hydro-df150-m.webp logitech-c920.webp; do
 cp "$repo/web/device-images/$name" "$stage/static/$name"
 cp "$repo/web/device-images/$name" "$stage/$name"
done
for f in gc-hero-leaf.webp mars-fc3000-transparent.webp mars-df150m-hires.webp; do
 base64 -d "$repo/cloud/staging/$f.b64" > "$stage/static/$f"
done
(cd "$stage/static" && sha256sum --check <<'CHECKSUMS'
43c5eb9ae1b2ba63e6c53cf897e2e348369693bcdab4669bcb4a5f1ab6a52e5b  gc-hero-leaf.webp
11f78a57c7f10a81d5a355f07b4a9b16b4c3a2769048914d5f3300d0a5c96c4f  mars-fc3000-transparent.webp
62d82caa752cbce47fcc42fb8adea84a18e6400eb0b87f9b66d35587ed69705f  mars-df150m-hires.webp
CHECKSUMS
)
grep -q 'cloud-master-bridge.js' "$stage/cloud-master.html"
grep -q 'dashboardSoilValue' "$stage/cloud-master.html"
grep -q 'Phasengerechtes Klima' "$stage/cloud-master.html"
grep -q 'soilTileReading(' "$stage/static/gc-final.js"
test -s "$stage/static/soil-sensor-reference.jpg"
grep -q 'gc-hero-leaf.webp' "$stage/static/gc-final.css"
grep -q 'mars-fc3000-transparent.webp' "$stage/static/gc-final.js"
grep -q 'mars-df150m-hires.webp' "$stage/static/gc-final.js"
test -d "$root" || { echo "Plesk cloud domain root missing" >&2; exit 1; }
for f in "$stage"/*; do
 [ -f "$f" ] || continue
 install -m 644 "$f" "$root/$(basename "$f")"
done
mkdir -p "$root/static"
for f in "$stage/static"/*; do
 install -m 644 "$f" "$root/static/$(basename "$f")"
done
echo "Grow Central cloud portal deployed from $(git -C "$repo" rev-parse --short HEAD)"
echo "HTTPS and authenticated WebSocket must still be tested independently."
