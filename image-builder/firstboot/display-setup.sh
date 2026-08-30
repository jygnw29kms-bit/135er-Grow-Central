#!/usr/bin/env bash
set -u

# 135er-Grow Central is intentionally headless from the big runtime rework onward.
# A local HDMI/touch kiosk is no longer part of the product architecture.
# Operation is provided through the responsive web UI / mobile clients.

STATE_DIR=/var/lib/135er-grow-central
BANNER=/etc/135er-grow-central/banner.txt

log() { printf '[grow-central-display] %s\n' "$*"; }
install -d -m 0750 -o growcentral -g growcentral "$STATE_DIR" 2>/dev/null || true

# Clean state left by older candidate images/upgrades.
rm -f \
  "$STATE_DIR/display-name" \
  "$STATE_DIR/display-mode" \
  "$STATE_DIR/display-connector" \
  "$STATE_DIR/display-kiosk-files-missing" \
  "$STATE_DIR/display-kiosk-packages-missing" \
  "$STATE_DIR/display-kiosk-started" \
  "$STATE_DIR/display-api-not-ready" 2>/dev/null || true

systemctl disable --now grow-central-display-kiosk.service >/dev/null 2>&1 || true
rm -f /etc/systemd/system/grow-central-display-kiosk.service 2>/dev/null || true
systemctl daemon-reload >/dev/null 2>&1 || true

printf '%s\n' 'headless' > "$STATE_DIR/display-policy"
chown growcentral:growcentral "$STATE_DIR/display-policy" 2>/dev/null || true
chmod 0640 "$STATE_DIR/display-policy" 2>/dev/null || true

log 'Headless product mode active; local HDMI/touch kiosk is permanently disabled.'

if [ -w /dev/tty1 ]; then
  {
    printf '\n'
    [ -r "$BANNER" ] && cat "$BANNER"
    printf '\n[BOOT] 135er-Grow Central\n'
    printf '[BOOT] Mode: headless controller\n'
    printf '[BOOT] Local web service: http://127.0.0.1:8080\n'
    printf '[BOOT] Administration: browser / mobile client\n\n'
  } > /dev/tty1 2>/dev/null || true
fi

exit 0
