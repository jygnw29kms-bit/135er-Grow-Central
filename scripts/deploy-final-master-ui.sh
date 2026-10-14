#!/usr/bin/env bash
set -Eeuo pipefail

REPO_RAW="https://raw.githubusercontent.com/jygnw29kms-bit/135er-Grow-Central/master"
TARGET="/opt/135er-grow-central/web"
STAMP="$(date +%Y%m%d-%H%M%S)"
BACKUP="/opt/135er-grow-central/data/ui-backup-${STAMP}"
TMP="$(mktemp -d /tmp/gc-final-master.XXXXXX)"
trap 'rm -rf "$TMP"' EXIT

if [[ ${EUID} -ne 0 ]]; then
  echo "Bitte mit sudo ausführen." >&2
  exit 1
fi

install -d -o growcentral -g growcentral "$BACKUP"
for f in platform.html platform.css platform.js platform-master.css platform-master.js; do
  [[ -f "$TARGET/$f" ]] && cp -a "$TARGET/$f" "$BACKUP/$f"
done

for f in platform.html platform-master.css platform-master.js; do
  echo "Lade $f ..."
  curl -fL --retry 3 --connect-timeout 10 "$REPO_RAW/web/$f" -o "$TMP/$f"
  test -s "$TMP/$f"
done

grep -q 'class="app-shell master-shell"' "$TMP/platform.html"
grep -q 'platform-master.css' "$TMP/platform.html"
grep -q 'platform-master.js' "$TMP/platform.html"
grep -q 'master-hero' "$TMP/platform-master.css"
grep -q 'loadOverviewAutomations' "$TMP/platform-master.js"

install -o root -g growcentral -m 0644 "$TMP/platform.html" "$TARGET/platform.html"
install -o root -g growcentral -m 0644 "$TMP/platform-master.css" "$TARGET/platform-master.css"
install -o root -g growcentral -m 0644 "$TMP/platform-master.js" "$TARGET/platform-master.js"

# Static files are served directly; restart is not required. Verify through the real app port.
HTTP="$(curl -sS -o "$TMP/live.html" -w '%{http_code}' http://127.0.0.1:8080/ || true)"
if [[ "$HTTP" != "200" ]]; then
  echo "Live-Prüfung fehlgeschlagen (HTTP $HTTP). Stelle vorherigen Stand wieder her." >&2
  for f in platform.html platform-master.css platform-master.js; do
    [[ -f "$BACKUP/$f" ]] && cp -a "$BACKUP/$f" "$TARGET/$f" || rm -f "$TARGET/$f"
  done
  exit 2
fi

grep -q 'class="app-shell master-shell"' "$TMP/live.html" || {
  echo "Master-Markierung fehlt in ausgelieferter Seite; Rollback." >&2
  for f in platform.html platform-master.css platform-master.js; do
    [[ -f "$BACKUP/$f" ]] && cp -a "$BACKUP/$f" "$TARGET/$f" || rm -f "$TARGET/$f"
  done
  exit 3
}

CSS_HTTP="$(curl -sS -o /dev/null -w '%{http_code}' http://127.0.0.1:8080/static/platform-master.css || true)"
JS_HTTP="$(curl -sS -o /dev/null -w '%{http_code}' http://127.0.0.1:8080/static/platform-master.js || true)"

echo "FINAL_MASTER_DEPLOYED"
echo "BACKUP=$BACKUP"
echo "ROOT_HTTP=$HTTP"
echo "MASTER_CSS_HTTP=$CSS_HTTP"
echo "MASTER_JS_HTTP=$JS_HTTP"
