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

systemctl restart 135er-grow-central.service
for _ in {1..20}; do
  if curl -fsS http://127.0.0.1:8080/api/health >/dev/null 2>&1; then break; fi
  sleep 1
done

ROOT_HTTP="$(curl -sS -o "$TMP/root.html" -w '%{http_code}' http://127.0.0.1:8080/ || true)"
UI_HTTP="$(curl -sS -o "$TMP/ui.html" -w '%{http_code}' http://127.0.0.1:8080/ui || true)"
CSS_HTTP="$(curl -sS -o /dev/null -w '%{http_code}' http://127.0.0.1:8080/static/platform-master.css || true)"
JS_HTTP="$(curl -sS -o /dev/null -w '%{http_code}' http://127.0.0.1:8080/static/platform-master.js || true)"
ROOM_JS_HTTP="$(curl -sS -o /dev/null -w '%{http_code}' http://127.0.0.1:8080/static/room_views.js || true)"

if [[ "$ROOT_HTTP" != "200" || "$UI_HTTP" != "200" || "$CSS_HTTP" != "200" || "$JS_HTTP" != "200" || "$ROOM_JS_HTTP" != "200" ]]; then
  echo "HTTP-Prüfung fehlgeschlagen: root=$ROOT_HTTP ui=$UI_HTTP css=$CSS_HTTP js=$JS_HTTP rooms=$ROOM_JS_HTTP" >&2
  rollback
  exit 2
fi

grep -q 'class="app-shell master-shell"' "$TMP/root.html" || { echo "Master-Markierung fehlt auf /." >&2; rollback; exit 3; }
grep -q 'class="app-shell master-shell"' "$TMP/ui.html" || { echo "Master-Markierung fehlt auf /ui." >&2; rollback; exit 4; }
if grep -q 'Räume & Growtagebuch' "$TMP/ui.html"; then
  echo "Legacy-Konsole wird weiterhin auf /ui ausgeliefert." >&2
  rollback
  exit 5
fi

echo "FINAL_MASTER_DEPLOYED"
echo "BACKUP=$BACKUP"
echo "ROOT_HTTP=$ROOT_HTTP"
echo "UI_HTTP=$UI_HTTP"
echo "MASTER_CSS_HTTP=$CSS_HTTP"
echo "MASTER_JS_HTTP=$JS_HTTP"
echo "ROOM_JS_HTTP=$ROOM_JS_HTTP"
echo "PRODUCTIVE_ROUTE=/ui"
