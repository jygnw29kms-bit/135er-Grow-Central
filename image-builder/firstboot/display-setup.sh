#!/usr/bin/env bash
set -u

STATE_DIR=/var/lib/135er-grow-central
BOOT_DIR=/boot/firmware
CONFIG="$BOOT_DIR/config.txt"
CMDLINE="$BOOT_DIR/cmdline.txt"
BANNER=/etc/135er-grow-central/banner.txt
KIOSK_UNIT_SOURCE=/opt/135er-grow-central/image-builder/firstboot/grow-central-display-kiosk.service
KIOSK_UNIT=/etc/systemd/system/grow-central-display-kiosk.service
KIOSK_SCRIPT=/opt/135er-grow-central/image-builder/firstboot/display-kiosk.sh

log() { printf '[grow-central-display] %s\n' "$*"; }
install -d -m 0750 -o growcentral -g growcentral "$STATE_DIR" 2>/dev/null || true

# Keep useful boot output available until the graphical kiosk takes tty1.
if [ -f "$CMDLINE" ]; then
  line="$(head -n1 "$CMDLINE")"
  line=" $(printf '%s' "$line" | tr -s ' ') "
  line="${line// quiet / }"
  line="${line// plymouth.ignore-serial-consoles / }"
  case " $line " in *" systemd.show_status="*) ;; *) line="$line systemd.show_status=true" ;; esac
  case " $line " in *" loglevel="*) ;; *) line="$line loglevel=4" ;; esac
  printf '%s\n' "$(printf '%s' "$line" | xargs)" > "$CMDLINE"
fi

# DRM may appear a few seconds after systemd starts on slower Pi 3 boots.
for _ in $(seq 1 20); do
  compgen -G '/sys/class/drm/card*-HDMI-A-*/status' >/dev/null && break
  sleep 1
done

DISPLAY_CONNECTED=false
DISPLAY_NAME=""
DISPLAY_MODE="auto"
CONNECTOR=""
FORCED_MODE=""

for status in /sys/class/drm/card*-HDMI-A-*/status; do
  [ -r "$status" ] || continue
  [ "$(cat "$status" 2>/dev/null)" = connected ] || continue
  DISPLAY_CONNECTED=true
  dir="${status%/status}"
  modes="$dir/modes"
  edid="$dir/edid"
  edid_text="$(strings "$edid" 2>/dev/null | tr '\n' ' ' || true)"
  mode_text="$(cat "$modes" 2>/dev/null || true)"
  base="$(basename "$dir")"
  CONNECTOR="${base#*-}"
  DISPLAY_NAME="HDMI display"
  if printf '%s' "$edid_text" | grep -Eqi 'elecrow|elcrow'; then DISPLAY_NAME="Elecrow HDMI touch display"; fi
  if printf '%s\n' "$mode_text" | grep -Fxq '1024x600'; then
    DISPLAY_MODE='1024x600M@60'; FORCED_MODE="$DISPLAY_MODE"; [ "$DISPLAY_NAME" != 'HDMI display' ] || DISPLAY_NAME='7-inch HDMI 1024x600'
  elif printf '%s\n' "$mode_text" | grep -Fxq '800x480'; then
    DISPLAY_MODE='800x480M@60'; FORCED_MODE="$DISPLAY_MODE"; [ "$DISPLAY_NAME" != 'HDMI display' ] || DISPLAY_NAME='7-inch HDMI 800x480'
  else
    first_mode="$(printf '%s\n' "$mode_text" | head -n1)"
    [ -z "$first_mode" ] || DISPLAY_MODE="$first_mode"
  fi
  break
 done

if $DISPLAY_CONNECTED && [ -n "$CONNECTOR" ]; then
  if [ -n "$FORCED_MODE" ] && [ -f "$CMDLINE" ]; then
    line="$(head -n1 "$CMDLINE")"
    line="$(printf '%s\n' "$line" | sed -E "s#(^| )video=${CONNECTOR}:[^ ]+##g" | xargs)"
    printf '%s video=%s:%sD\n' "$line" "$CONNECTOR" "$FORCED_MODE" > "$CMDLINE"
  fi
  if [ -f "$CONFIG" ]; then
    sed -i '/^# BEGIN 135ER-GROW-CENTRAL-DISPLAY$/,/^# END 135ER-GROW-CENTRAL-DISPLAY$/d' "$CONFIG"
    cat >> "$CONFIG" <<'EOF'
# BEGIN 135ER-GROW-CENTRAL-DISPLAY
disable_overscan=1
max_framebuffers=2
# END 135ER-GROW-CENTRAL-DISPLAY
EOF
  fi

  printf '%s\n' "$DISPLAY_NAME" > "$STATE_DIR/display-name"
  printf '%s\n' "$DISPLAY_MODE" > "$STATE_DIR/display-mode"
  printf '%s\n' "$CONNECTOR" > "$STATE_DIR/display-connector"
  chown growcentral:growcentral "$STATE_DIR/display-name" "$STATE_DIR/display-mode" "$STATE_DIR/display-connector" 2>/dev/null || true
  chmod 0640 "$STATE_DIR/display-name" "$STATE_DIR/display-mode" "$STATE_DIR/display-connector" 2>/dev/null || true

  if [ -r "$KIOSK_UNIT_SOURCE" ] && [ -r "$KIOSK_SCRIPT" ]; then
    chmod 0755 "$KIOSK_SCRIPT" 2>/dev/null || true
    install -o root -g root -m 0644 "$KIOSK_UNIT_SOURCE" "$KIOSK_UNIT" || true
    systemctl daemon-reload || true
    systemctl enable grow-central-display-kiosk.service >/dev/null 2>&1 || true
    systemctl start --no-block grow-central-display-kiosk.service >/dev/null 2>&1 || true
    log "Local GUI kiosk enabled for ${DISPLAY_NAME} on ${CONNECTOR} (${DISPLAY_MODE})."
  else
    touch "$STATE_DIR/display-kiosk-files-missing"
    log 'Kiosk files missing; diagnostic marker created.'
  fi
else
  rm -f "$STATE_DIR/display-name" "$STATE_DIR/display-mode" "$STATE_DIR/display-connector" 2>/dev/null || true
  log 'No connected HDMI display detected; keeping headless/network mode.'
fi

if [ -w /dev/tty1 ]; then
  {
    printf '\n'
    [ -r "$BANNER" ] && cat "$BANNER"
    printf '\n[BOOT] 135er-Grow Central hardware initialization\n'
    printf '[BOOT] Model: %s\n' "$(tr -d '\000' </proc/device-tree/model 2>/dev/null || echo unknown)"
    if $DISPLAY_CONNECTED; then
      printf '[BOOT] Display: %s · %s\n' "$DISPLAY_NAME" "$DISPLAY_MODE"
      printf '[BOOT] Local GUI: starting kiosk on tty1\n'
    else
      printf '[BOOT] Display: no connected HDMI panel\n'
      printf '[BOOT] Local GUI: headless/network mode\n'
    fi
    printf '[BOOT] Local web service: http://127.0.0.1:8080\n\n'
  } > /dev/tty1 2>/dev/null || true
fi

exit 0
