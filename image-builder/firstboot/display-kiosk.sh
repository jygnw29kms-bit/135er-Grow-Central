#!/usr/bin/env bash
set -euo pipefail

STATE_DIR=/var/lib/135er-grow-central
MODE_FILE="$STATE_DIR/display-mode"
NAME_FILE="$STATE_DIR/display-name"
USER=GrowCentral
HOME_DIR=/home/GrowCentral
SESSION=/usr/local/sbin/grow-central-display-session
MISSING_MARKER="$STATE_DIR/display-kiosk-packages-missing"
STARTED_MARKER="$STATE_DIR/display-kiosk-started"

log() { printf '[grow-central-kiosk] %s\n' "$*"; }

[ -s "$MODE_FILE" ] || { log 'No connected managed display; kiosk remains disabled.'; exit 0; }
MODE="$(cat "$MODE_FILE")"
NAME="$(cat "$NAME_FILE" 2>/dev/null || echo 'HDMI display')"
log "Display active: ${NAME} / ${MODE}"

# The release image must contain the graphical stack. Runtime installation is only
# an emergency recovery path after networking exists, never a first-boot dependency.
ensure_packages() {
  local missing=0
  for command in startx chromium openbox; do
    command -v "$command" >/dev/null 2>&1 || missing=1
  done
  if [ "$missing" -eq 0 ]; then
    rm -f "$MISSING_MARKER" 2>/dev/null || true
    return 0
  fi

  printf '%s\n' "$(date -u '+%Y-%m-%dT%H:%M:%SZ') graphical packages missing" > "$MISSING_MARKER"
  chmod 0640 "$MISSING_MARKER" 2>/dev/null || true
  chown growcentral:growcentral "$MISSING_MARKER" 2>/dev/null || true
  log 'ERROR: graphical packages missing from image; trying short online recovery.'

  if getent ahostsv4 deb.debian.org >/dev/null 2>&1; then
    export DEBIAN_FRONTEND=noninteractive
    timeout 240 apt-get update || true
    timeout 420 apt-get install -y --no-install-recommends \
      xserver-xorg-core xserver-xorg-input-libinput xinit openbox chromium unclutter x11-xserver-utils || true
  fi

  for command in startx chromium openbox; do
    command -v "$command" >/dev/null 2>&1 || { log "ERROR: ${command} unavailable."; return 1; }
  done
  rm -f "$MISSING_MARKER" 2>/dev/null || true
}

ensure_packages

mkdir -p /etc/X11
cat >/etc/X11/Xwrapper.config <<'EOF'
allowed_users=anybody
needs_root_rights=yes
EOF
chmod 0644 /etc/X11/Xwrapper.config

cat >"$SESSION" <<'EOF'
#!/usr/bin/env bash
set -euo pipefail
export HOME=/home/GrowCentral
export XDG_CONFIG_HOME="$HOME/.config"
export XDG_CACHE_HOME="$HOME/.cache"
mkdir -p "$XDG_CONFIG_HOME/openbox" "$XDG_CACHE_HOME" "$HOME/.config/chromium-growcentral"

xset s off || true
xset -dpms || true
xset s noblank || true
openbox-session >/tmp/grow-central-openbox.log 2>&1 &
unclutter -idle 0.4 -root >/dev/null 2>&1 &

# Wait only for the local API; internet access is deliberately irrelevant.
healthy=false
for _ in $(seq 1 120); do
  if curl --fail --silent --max-time 2 http://127.0.0.1:8080/api/health >/dev/null 2>&1; then
    healthy=true
    break
  fi
  sleep 1
done
if [ "$healthy" != true ]; then
  printf '%s\n' "$(date -u '+%Y-%m-%dT%H:%M:%SZ') local API not healthy before kiosk" \
    > /var/lib/135er-grow-central/display-api-not-ready 2>/dev/null || true
fi

MODE="$(cat /var/lib/135er-grow-central/display-mode 2>/dev/null || true)"
SCALE=1.00
case "$MODE" in
  800x480*) SCALE=1.00 ;;
  1024x600*) SCALE=1.10 ;;
  1280x720*) SCALE=1.00 ;;
  1920x1080*) SCALE=1.00 ;;
esac

exec chromium \
  --kiosk \
  --app=http://127.0.0.1/ui \
  --user-data-dir="$HOME/.config/chromium-growcentral" \
  --no-first-run \
  --no-default-browser-check \
  --noerrdialogs \
  --disable-infobars \
  --disable-session-crashed-bubble \
  --disable-translate \
  --disable-pinch \
  --overscroll-history-navigation=0 \
  --password-store=basic \
  --force-device-scale-factor="$SCALE" \
  --touch-events=enabled
EOF
chmod 0755 "$SESSION"
chown "$USER:$USER" "$SESSION" 2>/dev/null || true

systemctl stop getty@tty1.service 2>/dev/null || true
chown "$USER:tty" /dev/tty1 2>/dev/null || true
chmod 0620 /dev/tty1 2>/dev/null || true
install -d -o "$USER" -g "$USER" -m 0750 "$HOME_DIR/.config" "$HOME_DIR/.cache"
chown -R "$USER:$USER" "$HOME_DIR/.config" "$HOME_DIR/.cache" 2>/dev/null || true

printf '%s\n' "$(date -u '+%Y-%m-%dT%H:%M:%SZ') ${NAME} ${MODE}" > "$STARTED_MARKER"
chmod 0640 "$STARTED_MARKER" 2>/dev/null || true
chown growcentral:growcentral "$STARTED_MARKER" 2>/dev/null || true
log 'Starting local Grow Central touch GUI on tty1.'

exec runuser -u "$USER" -- env HOME="$HOME_DIR" USER="$USER" LOGNAME="$USER" \
  startx "$SESSION" -- :0 vt1 -keeptty -nolisten tcp
