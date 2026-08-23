#!/usr/bin/env bash
set -euo pipefail

STATE_DIR=/var/lib/135er-grow-central
MODE_FILE="$STATE_DIR/display-mode"
NAME_FILE="$STATE_DIR/display-name"
USER=GrowCentral
HOME_DIR=/home/GrowCentral
SESSION=/usr/local/sbin/grow-central-display-session

log() { printf '[grow-central-kiosk] %s\n' "$*"; }

[ -s "$MODE_FILE" ] || { log 'No managed 7-inch display detected; kiosk remains disabled.'; exit 0; }
MODE="$(cat "$MODE_FILE")"
NAME="$(cat "$NAME_FILE" 2>/dev/null || echo '7-inch HDMI')"
log "Display profile active: ${NAME} / ${MODE}"

# Wait for a usable uplink before attempting package installation. The kiosk is
# optional and must never block Grow Central networking or first-boot setup.
ensure_packages() {
  if command -v startx >/dev/null 2>&1 && command -v chromium >/dev/null 2>&1 && command -v openbox >/dev/null 2>&1; then
    return 0
  fi

  log 'Graphical kiosk packages are missing; waiting for LAN/WLAN internet.'
  for _ in $(seq 1 90); do
    if getent ahostsv4 deb.debian.org >/dev/null 2>&1 || getent ahostsv4 downloads.raspberrypi.com >/dev/null 2>&1; then
      break
    fi
    sleep 10
  done

  export DEBIAN_FRONTEND=noninteractive
  for attempt in 1 2 3; do
    if apt-get update && apt-get install -y --no-install-recommends \
      xserver-xorg-core xserver-xorg-input-libinput xinit openbox chromium unclutter x11-xserver-utils; then
      break
    fi
    log "Package installation attempt ${attempt} failed; retrying."
    sleep 20
  done

  command -v startx >/dev/null 2>&1 || { log 'startx unavailable after package installation.'; exit 1; }
  command -v chromium >/dev/null 2>&1 || { log 'Chromium unavailable after package installation.'; exit 1; }
  command -v openbox >/dev/null 2>&1 || { log 'Openbox unavailable after package installation.'; exit 1; }
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

for _ in $(seq 1 90); do
  curl --fail --silent --max-time 2 http://127.0.0.1:8080/api/health >/dev/null 2>&1 && break
  sleep 1
done

MODE="$(cat /var/lib/135er-grow-central/display-mode 2>/dev/null || true)"
SCALE=1.10
case "$MODE" in
  800x480*) SCALE=1.00 ;;
  1024x600*) SCALE=1.12 ;;
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

# Xorg must own tty1 while the kiosk is active; there is deliberately no shell
# autologin. SSH and the network GUI remain available in parallel.
systemctl stop getty@tty1.service 2>/dev/null || true

install -d -o "$USER" -g "$USER" -m 0750 "$HOME_DIR/.config" "$HOME_DIR/.cache"
chown -R "$USER:$USER" "$HOME_DIR/.config" "$HOME_DIR/.cache" 2>/dev/null || true

log 'Starting local Grow Central touch GUI.'
exec runuser -u "$USER" -- env HOME="$HOME_DIR" USER="$USER" LOGNAME="$USER" \
  startx "$SESSION" -- :0 vt1 -keeptty -nolisten tcp
