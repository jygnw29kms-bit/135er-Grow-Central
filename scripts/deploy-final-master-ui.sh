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

if [[ ${EUID} -ne 0 ]]; then
  echo "Bitte mit sudo ausführen." >&2
  exit 1
fi

install -d -o growcentral -g growcentral "$BACKUP/web" "$BACKUP/app"
WEB_FILES=(platform.html platform-master.css platform-master.js room_views.js)
APP_FILES=(gui_shell.py)
for f in "${WEB_FILES[@]}"; do [[ -f "$WEB/$f" ]] && cp -a "$WEB/$f" "$BACKUP/web/$f"; done
for f in "${APP_FILES[@]}"; do [[ -f "$APP/$f" ]] && cp -a "$APP/$f" "$BACKUP/app/$f"; done

rollback() {
  echo "Rollback auf $BACKUP ..." >&2
  for f in "${WEB_FILES[@]}"; do
    [[ -f "$BACKUP/web/$f" ]] && cp -a "$BACKUP/web/$f" "$WEB/$f"
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

# Pre-install integrity checks.
grep -q 'class="app-shell master-shell"' "$TMP/platform.html"
grep -q 'platform-master.css' "$TMP/platform.html"
grep -q 'platform-master.js' "$TMP/platform.html"
grep -q 'master-hero' "$TMP/platform-master.css"
grep -q 'loadOverviewAutomations' "$TMP/platform-master.js"
grep -q 'Kalibrierung erforderlich' "$TMP/room_views.js"
grep -q 'platform.html' "$TMP/gui_shell.py"
python3 -m py_compile "$TMP/gui_shell.py"

for f in "${WEB_FILES[@]}"; do install -o root -g growcentral -m 0644 "$TMP/$f" "$WEB/$f"; done
for f in "${APP_FILES[@]}"; do install -o root -g growcentral -m 0644 "$TMP/$f" "$APP/$f"; done

# Verify the files actually installed before restarting.
grep -q 'class="app-shell master-shell"' "$WEB/platform.html"
grep -q 'Kalibrierung erforderlich' "$WEB/room_views.js"
grep -q 'return FileResponse(WEB_DIR / "platform.html"' "$APP/gui_shell.py"

systemctl restart 135er-grow-central.service
for _ in {1..20}; do
  if curl -fsS http://127.0.0.1:8080/api/health >/dev/null 2>&1; then break; fi
  sleep 1
done

HEALTH_HTTP="$(curl -sS -o "$TMP/health.json" -w '%{http_code}' http://127.0.0.1:8080/api/health || true)"
ROOT_HTTP="$(curl -sS -D "$TMP/root.headers" -o "$TMP/root.html" -w '%{http_code}' http://127.0.0.1:8080/ || true)"
UI_HTTP="$(curl -sS -D "$TMP/ui.headers" -o "$TMP/ui.html" -w '%{http_code}' http://127.0.0.1:8080/ui || true)"
CSS_HTTP="$(curl -sS -o /dev/null -w '%{http_code}' http://127.0.0.1:8080/static/platform-master.css || true)"
JS_HTTP="$(curl -sS -o /dev/null -w '%{http_code}' http://127.0.0.1:8080/static/platform-master.js || true)"
ROOM_JS_HTTP="$(curl -sS -o /dev/null -w '%{http_code}' http://127.0.0.1:8080/static/room_views.js || true)"

# The GUI authentication middleware intentionally answers unauthenticated / and /ui
# requests with 303. That is healthy and must not trigger rollback.
if [[ "$HEALTH_HTTP" != "200" || "$CSS_HTTP" != "200" || "$JS_HTTP" != "200" || "$ROOM_JS_HTTP" != "200" ]]; then
  echo "Runtime/static Prüfung fehlgeschlagen: health=$HEALTH_HTTP css=$CSS_HTTP js=$JS_HTTP rooms=$ROOM_JS_HTTP" >&2
  rollback
  exit 2
fi
if [[ "$ROOT_HTTP" != "200" && "$ROOT_HTTP" != "303" ]]; then
  echo "Unerwarteter Status auf /: $ROOT_HTTP" >&2
  rollback
  exit 3
fi
if [[ "$UI_HTTP" != "200" && "$UI_HTTP" != "303" ]]; then
  echo "Unerwarteter Status auf /ui: $UI_HTTP" >&2
  rollback
  exit 4
fi

# If authentication is already present, verify the actual returned GUI too.
if [[ "$ROOT_HTTP" == "200" ]]; then
  grep -q 'class="app-shell master-shell"' "$TMP/root.html" || { echo "Master-Markierung fehlt auf /." >&2; rollback; exit 5; }
fi
if [[ "$UI_HTTP" == "200" ]]; then
  grep -q 'class="app-shell master-shell"' "$TMP/ui.html" || { echo "Master-Markierung fehlt auf /ui." >&2; rollback; exit 6; }
  if grep -q 'Räume & Growtagebuch' "$TMP/ui.html"; then
    echo "Legacy-Konsole wird weiterhin auf /ui ausgeliefert." >&2
    rollback
    exit 7
  fi
fi

ROOT_LOCATION="$(awk 'BEGIN{IGNORECASE=1}/^location:/{gsub("\r","");print $2;exit}' "$TMP/root.headers" || true)"
UI_LOCATION="$(awk 'BEGIN{IGNORECASE=1}/^location:/{gsub("\r","");print $2;exit}' "$TMP/ui.headers" || true)"

echo "FINAL_MASTER_DEPLOYED"
echo "BACKUP=$BACKUP"
echo "HEALTH_HTTP=$HEALTH_HTTP"
echo "ROOT_HTTP=$ROOT_HTTP${ROOT_LOCATION:+ -> $ROOT_LOCATION}"
echo "UI_HTTP=$UI_HTTP${UI_LOCATION:+ -> $UI_LOCATION}"
echo "MASTER_CSS_HTTP=$CSS_HTTP"
echo "MASTER_JS_HTTP=$JS_HTTP"
echo "ROOM_JS_HTTP=$ROOM_JS_HTTP"
echo "PRODUCTIVE_ROUTE=/ui"
