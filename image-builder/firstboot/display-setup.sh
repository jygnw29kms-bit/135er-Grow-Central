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

# Keep the boot console readable. The Grow Central Plymouth theme remains enabled,
# but kernel/systemd status is not intentionally hidden behind a completely quiet boot.
if [ -f "$CMDLINE" ]; then
  line="$(head -n1 "$CMDLINE")"
  line=" $(printf '%s' "$line" | tr -s ' ') "
  line="${line// quiet / }"
  line="${line// plymouth.ignore-serial-consoles / }"
  case " $line " in *" systemd.show_status="*) ;; *) line="$line systemd.show_status=true" ;; esac
  case " $line " in *" loglevel="*) ;; *) line="$line loglevel=4" ;; esac
  printf '%s\n' "$(printf '%s' "$line" | xargs)" > "$CMDLINE"
fi

# Detect a connected HDMI panel from DRM/EDID. Elecrow 7-inch panels commonly
# expose 1024x600 or 800x480. We only force a mode when such a panel is actually
# connected; normal monitors and headless systems retain firmware/KMS auto mode.
DISPLAY_NAME=""
DISPLAY_MODE=""
CONNECTOR=""
for status in /sys/class/drm/card*-HDMI-A-*/status; do
  [ -r "$status" ] || continue
  [ "$(cat "$status" 2>/dev/null)" = connected ] || continue
  dir="${status%/status}"
  modes="$dir/modes"
  edid="$dir/edid"
  edid_text="$(strings "$edid" 2>/dev/null | tr '\n' ' ' || true)"
  mode_text="$(cat "$modes" 2>/dev/null || true)"
  base="$(basename "$dir")"
  # Linux cmdline connector names omit the card prefix.
  CONNECTOR="${base#*-}"
  if printf '%s' "$edid_text" | grep -Eqi 'elecrow|elcrow'; then DISPLAY_NAME="Elecrow 7-inch HDMI"; fi
  if printf '%s\n' "$mode_text" | grep -Fxq '1024x600'; then DISPLAY_MODE='1024x600M@60'; [ -n "$DISPLAY_NAME" ] || DISPLAY_NAME='7-inch HDMI 1024x600'; break; fi
  if printf '%s\n' "$mode_text" | grep -Fxq '800x480'; then DISPLAY_MODE='800x480M@60'; [ -n "$DISPLAY_NAME" ] || DISPLAY_NAME='7-inch HDMI 800x480'; break; fi
  CONNECTOR=""
done

if [ -n "$DISPLAY_MODE" ] && [ -n "$CONNECTOR" ]; then
  if [ -f "$CMDLINE" ]; then
    line="$(head -n1 "$CMDLINE")"
    # Remove only an earlier Grow-Central managed mode for this HDMI connector.
    line="$(printf '%s\n' "$line" | sed -E "s#(^| )video=${CONNECTOR}:[^ ]+##g" | xargs)"
    printf '%s video=%s:%sD\n' "$line" "$CONNECTOR" "$DISPLAY_MODE" > "$CMDLINE"
  fi
  if [ -f "$CONFIG" ]; then
    sed -i '/^# BEGIN 135ER-GROW-CENTRAL-DISPLAY$/,/^# END 135ER-GROW-CENTRAL-DISPLAY$/d' "$CONFIG"
    cat >> "$CONFIG" <<'EOF'
# BEGIN 135ER-GROW-CENTRAL-DISPLAY
# Managed by Grow Central. KMS/EDID remains primary; overscan is disabled for
# small HDMI touch displays and framebuffer allocation stays conservative.
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
  log "Detected ${DISPLAY_NAME} on ${CONNECTOR}; next boot mode ${DISPLAY_MODE}."

  # Install the local kiosk unit only for a supported 7-inch panel. The kiosk
  # script itself waits for networking and installs its graphical dependencies
  # when needed, so first-boot AP functionality never depends on display setup.
  if [ -r "$KIOSK_UNIT_SOURCE" ] && [ -x "$KIOSK_SCRIPT" ]; then
    install -o root -g root -m 0644 "$KIOSK_UNIT_SOURCE" "$KIOSK_UNIT" || true
    systemctl daemon-reload || true
    systemctl enable grow-central-display-kiosk.service >/dev/null 2>&1 || true
    systemctl start --no-block grow-central-display-kiosk.service >/dev/null 2>&1 || true
    log 'Elecrow local GUI kiosk enabled.'
  else
    log 'Kiosk files missing; display remains console-only.'
  fi
else
  rm -f "$STATE_DIR/display-name" "$STATE_DIR/display-mode" "$STATE_DIR/display-connector" 2>/dev/null || true
  if [ -f "$KIOSK_UNIT" ]; then
    systemctl disable --now grow-central-display-kiosk.service >/dev/null 2>&1 || true
  fi
  log 'No Grow Central 7-inch HDMI profile detected; leaving HDMI mode on EDID/KMS automatic.'
fi

# Put the project mark and a concise live boot summary on tty1 as soon as the
# first-boot hardware stage runs. Do not steal stdin or create an autologin.
if [ -w /dev/tty1 ]; then
  {
    printf '\n'
    [ -r "$BANNER" ] && cat "$BANNER"
    printf '\n[BOOT] 135er-Grow Central hardware initialization\n'
    printf '[BOOT] Model: %s\n' "$(tr -d '\000' </proc/device-tree/model 2>/dev/null || echo unknown)"
    if [ -n "$DISPLAY_MODE" ]; then
      printf '[BOOT] Display: %s · %s\n' "$DISPLAY_NAME" "$DISPLAY_MODE"
      printf '[BOOT] Local GUI: Elecrow touch kiosk enabled\n'
    else
      printf '[BOOT] Display: HDMI/KMS automatic or headless\n'
      printf '[BOOT] Local GUI: headless/network mode\n'
    fi
    printf '[BOOT] Console status: visible · Plymouth branding: enabled\n\n'
  } > /dev/tty1 2>/dev/null || true
fi

exit 0
