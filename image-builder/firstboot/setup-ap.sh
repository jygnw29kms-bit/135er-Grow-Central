#!/usr/bin/env bash
set -euo pipefail

CONNECTION="grow-central-setup-ap"
ADDRESS="10.42.0.1/24"
STATE_DIR="/var/lib/135er-grow-central"
CERT_DIR="/etc/135er-grow-central"
WLAN="wlan0"
REGDOMAIN="DE"

log() {
  printf '[grow-central-setup-ap] %s\n' "$*"
}

fail() {
  printf '[grow-central-setup-ap] ERROR: %s\n' "$*" >&2
  rfkill list >&2 || true
  nmcli general status >&2 || true
  nmcli device status >&2 || true
  ip link show "$WLAN" >&2 || true
  iw dev "$WLAN" info >&2 || true
  systemctl --no-pager --full status bluetooth.service >&2 || true
  exit 1
}

install -d -o growcentral -g growcentral -m 0750 "$STATE_DIR"
install -d -o root -g growcentral -m 0750 "$CERT_DIR"

MODEL="$(tr -d '\000' </proc/device-tree/model 2>/dev/null || true)"
case "$MODEL" in
  *"Raspberry Pi 3 Model B"*) PLATFORM="pi3b" ;;
  *"Raspberry Pi 4 Model B"*) PLATFORM="pi4" ;;
  *"Raspberry Pi 5 Model B"*) PLATFORM="pi5" ;;
  *"Raspberry Pi"*) PLATFORM="raspberrypi" ;;
  *) PLATFORM="unknown" ;;
esac
log "Hardware: ${MODEL:-unknown} profile=${PLATFORM}"
printf '%s\n' "${MODEL:-unknown}" >"${STATE_DIR}/hardware-model"
printf '%s\n' "$PLATFORM" >"${STATE_DIR}/hardware-profile"
chown growcentral:growcentral "${STATE_DIR}/hardware-model" "${STATE_DIR}/hardware-profile" || true
chmod 0640 "${STATE_DIR}/hardware-model" "${STATE_DIR}/hardware-profile" || true

# Initialise the common radio stack on Pi 3B, 4 and 5.  The Pi 3B is the most
# timing-sensitive because Wi-Fi/Bluetooth share the older Broadcom combo chip.
rfkill unblock bluetooth || true
systemctl start bluetooth.service || true
for _ in $(seq 1 15); do
  if command -v bluetoothctl >/dev/null 2>&1 && bluetoothctl show 2>/dev/null | grep -q '^Controller\|Powered:'; then
    bluetoothctl power on >/dev/null 2>&1 || true
    break
  fi
  sleep 1
done

if nmcli -t -f NAME,DEVICE connection show --active | grep -Fxq "grow-central-uplink:${WLAN}"; then
  log "Home WLAN is already active; setup AP is not required."
  exit 0
fi

# Pi 3B uses BCM43430 (2.4 GHz only); Pi 4/5 also support this conservative
# 2.4-GHz setup channel.  Explicitly clear rfkill and set the regulatory domain
# on every platform so the same image behaves deterministically.
rfkill unblock wifi || true
nmcli radio wifi on || true
iw reg set "$REGDOMAIN" || true

# Broadcom/RP1 backed interfaces can appear after NetworkManager during a cold
# boot. Wait for the real device instead of assuming Pi-4 timing.
for _ in $(seq 1 30); do
  [ -e "/sys/class/net/${WLAN}" ] && break
  sleep 1
done
[ -e "/sys/class/net/${WLAN}" ] || fail "${WLAN} did not appear within 30 seconds"

nmcli device set "$WLAN" managed yes || true
ip link set "$WLAN" up || true

# Ethernet is optional during first boot, but ensure the interface is usable
# when present. NetworkManager remains responsible for address configuration.
if [ -e /sys/class/net/eth0 ]; then
  nmcli device set eth0 managed yes >/dev/null 2>&1 || true
  ip link set eth0 up >/dev/null 2>&1 || true
fi

for _ in $(seq 1 20); do
  STATE="$(nmcli -g GENERAL.STATE device show "$WLAN" 2>/dev/null || true)"
  case "$STATE" in
    20*|30*|40*|50*|60*|70*|80*|90*|100*) break ;;
  esac
  sleep 1
done

# Refuse to continue if the loaded driver itself does not advertise AP mode.
if ! iw list 2>/dev/null | awk '
  /Supported interface modes:/ {m=1; next}
  m && /^[[:space:]]*\*/ { if ($2 == "AP") found=1; next }
  m && !/^[[:space:]]/ {m=0}
  END {exit !found}
'; then
  fail "Wi-Fi driver does not report AP mode support"
fi

MAC_SUFFIX="$(tr -d ':' < "/sys/class/net/${WLAN}/address" | tail -c 5 | tr '[:lower:]' '[:upper:]')"
SSID="135er-GrowCentral-Setup-${MAC_SUFFIX}"

# Recreate the profile on every unprovisioned boot. This deliberately removes
# stale MAC/802.1X/security state across Pi 3B, 4 and 5.
nmcli connection down "$CONNECTION" >/dev/null 2>&1 || true
nmcli connection delete "$CONNECTION" >/dev/null 2>&1 || true

nmcli connection add \
  type wifi \
  ifname "$WLAN" \
  con-name "$CONNECTION" \
  ssid "$SSID"

nmcli connection modify "$CONNECTION" \
  connection.interface-name "$WLAN" \
  connection.autoconnect yes \
  connection.autoconnect-priority 100 \
  802-11-wireless.mode ap \
  802-11-wireless.band bg \
  802-11-wireless.channel 1 \
  802-11-wireless.powersave 2 \
  802-11-wireless-security.key-mgmt wpa-psk \
  802-11-wireless-security.psk grow-central-test \
  ipv4.method shared \
  ipv4.addresses "$ADDRESS" \
  ipv4.never-default yes \
  ipv4.ignore-auto-dns yes \
  ipv6.method disabled

if ! nmcli --wait 35 connection up "$CONNECTION"; then
  log "First AP activation failed; resetting WLAN and retrying once."
  nmcli connection down "$CONNECTION" >/dev/null 2>&1 || true
  rfkill unblock wifi || true
  nmcli radio wifi off || true
  sleep 2
  nmcli radio wifi on || true
  iw reg set "$REGDOMAIN" || true
  ip link set "$WLAN" up || true
  sleep 3
  nmcli --wait 35 connection up "$CONNECTION" || fail "NetworkManager could not activate the setup AP"
fi

for _ in $(seq 1 25); do
  if ip -4 address show dev "$WLAN" | grep -Fq "$ADDRESS" \
    && ss -H -lun | awk '$4 ~ /:67$/ { found=1 } END { exit !found }'; then
    log "READY: model=${MODEL:-unknown} profile=${PLATFORM} SSID=${SSID} ADDRESS=${ADDRESS}"
    exit 0
  fi
  sleep 1
done

fail "Setup AP did not acquire ${ADDRESS} with an active DHCP listener"

# CI trigger: universal Raspberry Pi 3B/4/5 compatibility image.
