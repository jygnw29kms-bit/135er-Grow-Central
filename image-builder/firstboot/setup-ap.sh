#!/usr/bin/env bash
set -euo pipefail

CONNECTION="grow-central-setup-ap"
WLAN="wlan0"
ADDRESS="10.42.0.1/24"
DHCP_RANGE="10.42.0.10,10.42.0.250"
STATE_DIR="/var/lib/135er-grow-central"
CERT_DIR="/etc/135er-grow-central"
REGDOMAIN="DE"

log() {
  printf '[grow-central-setup-ap] %s\n' "$*"
}

fail() {
  printf '[grow-central-setup-ap] ERROR: %s\n' "$*" >&2
  printf '%s\n' '--- hardware ---' >&2
  tr -d '\000' </proc/device-tree/model 2>/dev/null >&2 || true
  uname -a >&2 || true
  printf '%s\n' '--- radio/network ---' >&2
  rfkill list >&2 || true
  nmcli general status >&2 || true
  nmcli radio >&2 || true
  nmcli device status >&2 || true
  ip -br link >&2 || true
  ip -br addr >&2 || true
  iw dev >&2 || true
  iw reg get >&2 || true
  journalctl -u NetworkManager.service -b --no-pager -n 40 >&2 || true
  exit 1
}

for command in nmcli ip iw rfkill ss awk grep tr tail systemctl; do
  command -v "$command" >/dev/null 2>&1 || fail "required command missing: $command"
done

install -d -o growcentral -g growcentral -m 0750 "$STATE_DIR"
install -d -o root -g growcentral -m 0750 "$CERT_DIR"

# The CI image smoke test runs in a container without Raspberry Pi radio hardware.
if systemd-detect-virt --quiet --container; then
  log "Container smoke boot detected; skipping physical wlan0 setup."
  exit 0
fi

MODEL="$(tr -d '\000' </proc/device-tree/model 2>/dev/null || true)"
case "$MODEL" in
  *"Raspberry Pi 4 Model B"*)
    PLATFORM="pi4"
    EXPECTED_SOC="BCM2711"
    ;;
  *"Raspberry Pi 3 Model B"*)
    PLATFORM="pi3b"
    EXPECTED_SOC="BCM2837"
    ;;
  *"Raspberry Pi 5 Model B"*)
    PLATFORM="pi5"
    EXPECTED_SOC="BCM2712"
    ;;
  *"Raspberry Pi"*)
    PLATFORM="raspberrypi"
    EXPECTED_SOC="unknown"
    ;;
  *)
    PLATFORM="unknown"
    EXPECTED_SOC="unknown"
    ;;
esac

log "Hardware model=${MODEL:-unknown} profile=${PLATFORM} expected_soc=${EXPECTED_SOC} wlan=${WLAN}"
printf '%s\n' "${MODEL:-unknown}" >"${STATE_DIR}/hardware-model"
printf '%s\n' "$PLATFORM" >"${STATE_DIR}/hardware-profile"
printf '%s\n' "$WLAN" >"${STATE_DIR}/hardware-wlan-interface"
chown growcentral:growcentral "$STATE_DIR/hardware-model" "$STATE_DIR/hardware-profile" "$STATE_DIR/hardware-wlan-interface" || true
chmod 0640 "$STATE_DIR/hardware-model" "$STATE_DIR/hardware-profile" "$STATE_DIR/hardware-wlan-interface" || true

# Raspberry Pi 4 reference hardware: BCM2711, onboard dual-band 802.11ac WLAN,
# Bluetooth 5.0/BLE and Gigabit Ethernet. The first-boot AP intentionally stays
# on 2.4 GHz channel 1 for maximum client compatibility and preserves wlan0,
# which was the interface used by the last hardware-confirmed setup build.
if [ "$PLATFORM" = "pi4" ]; then
  log "Applying Raspberry Pi 4 WLAN profile: wlan0, 2.4 GHz, channel 1, AP mode."
fi

systemctl is-active --quiet NetworkManager.service || systemctl start NetworkManager.service

# If the configured home WLAN is already active, do not steal wlan0 back for AP use.
if nmcli -t -f NAME,DEVICE connection show --active | grep -Fxq "grow-central-uplink:${WLAN}"; then
  log "Home WLAN is already active on ${WLAN}; setup AP is not required."
  exit 0
fi

rfkill unblock wifi || true
nmcli radio wifi on
iw reg set "$REGDOMAIN" || true

# Preserve the Raspberry Pi OS wlan0 interface naming used by the confirmed Pi 4 build.
for _ in $(seq 1 40); do
  [ -e "/sys/class/net/${WLAN}" ] && break
  sleep 1
done
[ -e "/sys/class/net/${WLAN}" ] || fail "${WLAN} did not appear within 40 seconds"

nmcli device set "$WLAN" managed yes || true
ip link set dev "$WLAN" up || true

# Wait until NetworkManager knows the physical radio. Do not fail merely because
# the device is disconnected; disconnected is the expected state before AP activation.
for _ in $(seq 1 30); do
  DEVICE_TYPE="$(nmcli -g GENERAL.TYPE device show "$WLAN" 2>/dev/null || true)"
  [ "$DEVICE_TYPE" = "wifi" ] && break
  sleep 1
done
[ "$(nmcli -g GENERAL.TYPE device show "$WLAN" 2>/dev/null || true)" = "wifi" ] || fail "NetworkManager does not expose ${WLAN} as Wi-Fi"

# Verify AP capability without making the parser dependent on exact iw indentation.
if ! iw list 2>/dev/null | grep -Eq '^[[:space:]]*\*[[:space:]]+AP([[:space:]]|$)'; then
  fail "Wi-Fi driver does not advertise AP mode"
fi

MAC="$(cat "/sys/class/net/${WLAN}/address" 2>/dev/null || true)"
[ -n "$MAC" ] || fail "could not read ${WLAN} MAC address"
MAC_SUFFIX="$(printf '%s' "$MAC" | tr -d ':' | tail -c 5 | tr '[:lower:]' '[:upper:]')"
SSID="135er-GrowCentral-Setup-${MAC_SUFFIX}"

# Return to the minimal, hardware-confirmed NetworkManager profile used by the
# working Pi 4 generation. Recreate it to remove stale MAC/security state.
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
  wifi-sec.key-mgmt wpa-psk \
  wifi-sec.psk grow-central-test \
  ipv4.method shared \
  ipv4.addresses "$ADDRESS" \
  ipv4.shared-dhcp-range "$DHCP_RANGE" \
  ipv4.shared-dhcp-lease-time 3600 \
  ipv4.never-default yes \
  ipv4.ignore-auto-dns yes \
  ipv6.method disabled

# Confirm that the installed NetworkManager accepted the complete profile before activation.
nmcli -f connection.interface-name,802-11-wireless.mode,802-11-wireless.band,802-11-wireless.channel,ipv4.method,ipv4.addresses connection show "$CONNECTION" >/dev/null \
  || fail "NetworkManager rejected the setup AP profile"

if ! nmcli --wait 40 connection up "$CONNECTION"; then
  log "First AP activation failed; performing one controlled wlan0 retry."
  nmcli connection down "$CONNECTION" >/dev/null 2>&1 || true
  rfkill unblock wifi || true
  nmcli radio wifi off || true
  sleep 2
  nmcli radio wifi on || true
  iw reg set "$REGDOMAIN" || true
  ip link set dev "$WLAN" up || true
  sleep 3
  nmcli --wait 40 connection up "$CONNECTION" || fail "NetworkManager could not activate the setup AP"
fi

for _ in $(seq 1 30); do
  if ip -4 address show dev "$WLAN" | grep -Fq "$ADDRESS" \
    && ss -H -lun | awk '$4 ~ /:67$/ { found=1 } END { exit !found }'; then
    log "READY: model=${MODEL:-unknown} profile=${PLATFORM} interface=${WLAN} SSID=${SSID} ADDRESS=${ADDRESS} DHCP=${DHCP_RANGE}"
    exit 0
  fi
  sleep 1
done

fail "Setup AP did not acquire ${ADDRESS} with an active DHCP listener"
