#!/usr/bin/env bash
set -Eeuo pipefail

REPO_RAW="https://raw.githubusercontent.com/jygnw29kms-bit/135er-Grow-Central/master"
ROOT="/opt/135er-grow-central"
WEB="$ROOT/web"
APP="$ROOT/app"
STAMP="$(date +%Y%m%d-%H%M%S)"
BACKUP="$ROOT/data/ui-backup-${STAMP}"
TMP="$(mktemp -d /tmp/gc-final-master.XXXXXX)"
trap 'rm -rf "$TMP"' EXIT

# Free-to-use Unsplash photograph, mirrored by Grow with Jane. Downloaded once and served locally.
GROW_ART_URL="https://i0.wp.com/growithjane.com/wp-content/uploads/2024/09/crystalweed-cannabis-alN0L6LHlt0-unsplash.jpg?resize=900%2C600&ssl=1"

if [[ ${EUID} -ne 0 ]]; then
  echo "Bitte mit sudo ausführen." >&2
  exit 1
fi

install -d -o growcentral -g growcentral "$BACKUP/web" "$BACKUP/app"
WEB_FILES=(platform.html platform.js runtime_status.js platform-master.css platform-master.js platform-visual.css room_views.js console.html console.js console.css mobile.html mobile.js ui-editor.html ui-editor.js session_write.js mobile_runtime_fix.css mobile_runtime_fix.js)
IMAGE_FILES=(master-grow-hero.jpg master-grow-room.jpg)
APP_FILES=(gui_shell.py)
for f in "${WEB_FILES[@]}" "${IMAGE_FILES[@]}"; do [[ -f "$WEB/$f" ]] && cp -a "$WEB/$f" "$BACKUP/web/$f"; done
for f in "${APP_FILES[@]}"; do [[ -f "$APP/$f" ]] && cp -a "$APP/$f" "$BACKUP/app/$f"; done

rollback() {
  echo "Rollback auf $BACKUP ..." >&2
  for f in "${WEB_FILES[@]}" "${IMAGE_FILES[@]}"; do
    [[ -f "$BACKUP/web/$f" ]] && cp -a "$BACKUP/web/$f" "$WEB/$f" || rm -f "$WEB/$f"
  done
  for f in "${APP_FILES[@]}"; do
    [[ -f "$BACKUP/app/$f" ]] && cp -a "$BACKUP/app/$f" "$APP/$f"
  done
  systemctl restart 135er-grow-central.service || true
}

for f in "${WEB_FILES[@]}"; do
  echo "Lade web/$f ..."
  curl -fL --retry 3 --connect-timeout 10 "$REPO_RAW/web/$f" -o "$TMP/$f"
  test -s "$TMP/$f"
done
for f in "${APP_FILES[@]}"; do
  echo "Lade app/$f ..."
  curl -fL --retry 3 --connect-timeout 10 "$REPO_RAW/app/$f" -o "$TMP/$f"
  test -s "$TMP/$f"
done

echo "Lade lokale Final-Master Bildmotive ..."
curl -fL --retry 3 --connect-timeout 15 "$GROW_ART_URL" -o "$TMP/master-grow-hero.jpg"
cp "$TMP/master-grow-hero.jpg" "$TMP/master-grow-room.jpg"
[[ $(stat -c%s "$TMP/master-grow-hero.jpg") -gt 20000 ]]

# Pre-install integrity checks.
grep -q 'class="app-shell master-shell"' "$TMP/platform.html"
grep -q 'platform-master.css' "$TMP/platform.html"
grep -q 'platform-master.js' "$TMP/platform.html"
grep -q 'master-hero' "$TMP/platform-master.css"
grep -q 'loadOverviewAutomations' "$TMP/platform-master.js"
grep -q 'platform-visual.css' "$TMP/platform-master.js"
grep -q 'master-grow-hero.jpg' "$TMP/platform-visual.css"
grep -q 'Kalibrierung erforderlich' "$TMP/room_views.js"
grep -q 'platform.html' "$TMP/gui_shell.py"
python3 -m py_compile "$TMP/gui_shell.py"

for f in "${WEB_FILES[@]}"; do install -o root -g growcentral -m 0644 "$TMP/$f" "$WEB/$f"; done
for f in "${IMAGE_FILES[@]}"; do install -o root -g growcentral -m 0644 "$TMP/$f" "$WEB/$f"; done
for f in "${APP_FILES[@]}"; do install -o root -g growcentral -m 0644 "$TMP/$f" "$APP/$f"; done

# Verify files before restart.
grep -q 'class="app-shell master-shell"' "$WEB/platform.html"
grep -q 'Kalibrierung erforderlich' "$WEB/room_views.js"
grep -q 'return FileResponse(WEB_DIR / "platform.html"' "$APP/gui_shell.py"
[[ -s "$WEB/master-grow-hero.jpg" && -s "$WEB/master-grow-room.jpg" ]]

systemctl restart 135er-grow-central.service
for _ in {1..20}; do
  if curl -fsS http://127.0.0.1:8080/api/health >/dev/null 2>&1; then break; fi
  sleep 1
done

HEALTH_HTTP="$(curl -sS -o "$TMP/health.json" -w '%{http_code}' http://127.0.0.1:8080/api/health || true)"
ROOT_HTTP="$(curl -sS -D "$TMP/root.headers" -o "$TMP/root.html" -w '%{http_code}' http://127.0.0.1:8080/ || true)"
UI_HTTP="$(curl -sS -D "$TMP/ui.headers" -o "$TMP/ui.html" -w '%{http_code}' http://127.0.0.1:8080/ui || true)"
ROOMS_HTTP="$(curl -sS -o "$TMP/rooms.html" -w '%{http_code}' http://127.0.0.1:8080/rooms || true)"
CSS_HTTP="$(curl -sS -o /dev/null -w '%{http_code}' http://127.0.0.1:8080/static/platform-master.css || true)"
VISUAL_HTTP="$(curl -sS -o /dev/null -w '%{http_code}' http://127.0.0.1:8080/static/platform-visual.css || true)"
JS_HTTP="$(curl -sS -o /dev/null -w '%{http_code}' http://127.0.0.1:8080/static/platform-master.js || true)"
ROOM_JS_HTTP="$(curl -sS -o /dev/null -w '%{http_code}' http://127.0.0.1:8080/static/room_views.js || true)"
HERO_HTTP="$(curl -sS -o /dev/null -w '%{http_code}' http://127.0.0.1:8080/static/master-grow-hero.jpg || true)"
ROOM_ART_HTTP="$(curl -sS -o /dev/null -w '%{http_code}' http://127.0.0.1:8080/static/master-grow-room.jpg || true)"

if [[ "$HEALTH_HTTP" != "200" || "$CSS_HTTP" != "200" || "$VISUAL_HTTP" != "200" || "$JS_HTTP" != "200" || "$ROOM_JS_HTTP" != "200" || "$HERO_HTTP" != "200" || "$ROOM_ART_HTTP" != "200" ]]; then
  echo "Runtime/static Prüfung fehlgeschlagen: health=$HEALTH_HTTP css=$CSS_HTTP visual=$VISUAL_HTTP js=$JS_HTTP rooms=$ROOM_JS_HTTP hero=$HERO_HTTP roomart=$ROOM_ART_HTTP" >&2
  rollback
  exit 2
fi
if [[ "$ROOT_HTTP" != "200" && "$ROOT_HTTP" != "303" ]]; then echo "Unerwarteter Status auf /: $ROOT_HTTP" >&2; rollback; exit 3; fi
if [[ "$UI_HTTP" != "200" && "$UI_HTTP" != "303" ]]; then echo "Unerwarteter Status auf /ui: $UI_HTTP" >&2; rollback; exit 4; fi

if [[ "$ROOMS_HTTP" != "200" && "$ROOMS_HTTP" != "303" ]]; then echo "Unerwarteter Status auf /rooms: $ROOMS_HTTP" >&2; rollback; exit 8; fi
if [[ "$ROOMS_HTTP" == "200" ]]; then grep -q 'id="roomDialog"' "$TMP/rooms.html" || { echo "Raumverwaltung fehlt auf /rooms." >&2; rollback; exit 9; }; fi

if [[ "$ROOT_HTTP" == "200" ]]; then grep -q 'class="app-shell master-shell"' "$TMP/root.html" || { echo "Master-Markierung fehlt auf /." >&2; rollback; exit 5; }; fi
if [[ "$UI_HTTP" == "200" ]]; then
  grep -q 'class="app-shell master-shell"' "$TMP/ui.html" || { echo "Master-Markierung fehlt auf /ui." >&2; rollback; exit 6; }
  if grep -q 'Räume & Growtagebuch' "$TMP/ui.html"; then echo "Legacy-Konsole wird weiterhin auf /ui ausgeliefert." >&2; rollback; exit 7; fi
fi

ROOT_LOCATION="$(awk 'BEGIN{IGNORECASE=1}/^location:/{gsub("\r","");print $2;exit}' "$TMP/root.headers" || true)"
UI_LOCATION="$(awk 'BEGIN{IGNORECASE=1}/^location:/{gsub("\r","");print $2;exit}' "$TMP/ui.headers" || true)"

echo "FINAL_MASTER_DEPLOYED"
echo "BACKUP=$BACKUP"
echo "HEALTH_HTTP=$HEALTH_HTTP"
echo "ROOT_HTTP=$ROOT_HTTP${ROOT_LOCATION:+ -> $ROOT_LOCATION}"
echo "UI_HTTP=$UI_HTTP${UI_LOCATION:+ -> $UI_LOCATION}"
echo "MASTER_CSS_HTTP=$CSS_HTTP"
echo "VISUAL_CSS_HTTP=$VISUAL_HTTP"
echo "MASTER_JS_HTTP=$JS_HTTP"
echo "ROOM_JS_HTTP=$ROOM_JS_HTTP"
echo "HERO_ART_HTTP=$HERO_HTTP"
echo "ROOM_ART_HTTP=$ROOM_ART_HTTP"
echo "PRODUCTIVE_ROUTE=/ui"
echo "ROOM_WORKSPACE_HTTP=$ROOMS_HTTP"
