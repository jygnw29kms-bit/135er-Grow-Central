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
  exit 1
}

install -d -o growcentral -g growcentral -m 0750 "$STATE_DIR"
install -d -o root -g growcentral -m 0750 "$CERT_DIR"

# If first-boot already handed wlan0 to the selected home WLAN, never replace it.
if nmcli -t -f NAME,DEVICE connection show --active | grep -Fxq "grow-central-uplink:${WLAN}"; then
  log "Home WLAN is already active; setup AP is not required."
  exit 0
fi

# Raspberry Pi 3B (BCM43430) is 2.4-GHz only and may come up rfkill-blocked
# or without a regulatory domain. Pi 4 is more forgiving, therefore do all
# of this explicitly so the same image is deterministic on both boards.
rfkill unblock wifi || true
nmcli radio wifi on || true
iw reg set "$REGDOMAIN" || true

# brcmfmac can appear a few seconds after NetworkManager during cold boot.
for _ in $(seq 1 30); do
  [ -e "/sys/class/net/${WLAN}" ] && break
  sleep 1
done
[ -e "/sys/class/net/${WLAN}" ] || fail "${WLAN} did not appear within 30 seconds"

# Make sure NetworkManager owns the interface and the kernel device is up.
nmcli device set "$WLAN" managed yes || true
ip link set "$WLAN" up || true

for _ in $(seq 1 20); do
  STATE="$(nmcli -g GENERAL.STATE device show "$WLAN" 2>/dev/null || true)"
  case "$STATE" in
    20*|30*|40*|50*|60*|70*|80*|90*|100*) break ;;
  esac
  sleep 1
done

# Pi 3B must advertise AP capability through brcmfmac. Abort with a useful
# diagnostic instead of creating a connection profile that can never activate.
if ! iw list 2>/dev/null | awk '
  /Supported interface modes:/ {m=1; next}
  m && /^\s*\*/ { if ($2 == "AP") found=1; next }
  m && !/^\s/ {m=0}
  END {exit !found}
'; then
  fail "Wi-Fi driver does not report AP mode support"
fi

MAC_SUFFIX="$(tr -d ':' < "/sys/class/net/${WLAN}/address" | tail -c 5 | tr '[:lower:]' '[:upper:]')"
SSID="135er-GrowCentral-Setup-${MAC_SUFFIX}"

# Always recreate the unprovisioned AP profile. This removes stale MAC,
# 802.1X and security properties that can make a Pi-4-created profile
# incompatible with the BCM43430 in the Pi 3B.
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

# A first attempt can race brcmfmac/wpa_supplicant on Pi 3B. Retry once after
# resetting the radio instead of leaving the device at a login console.
if ! nmcli --wait 35 connection up "$CONNECTION"; then
  log "First AP activation failed; resetting Pi WLAN and retrying once."
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
    log "READY: SSID=${SSID} ADDRESS=${ADDRESS}"
    exit 0
  fi
  sleep 1
done

fail "Setup AP did not acquire ${ADDRESS} with an active DHCP listener"
