#!/usr/bin/env bash
set -euo pipefail

CONNECTION="grow-central-setup-ap"
WLAN=""
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
  printf '%s\n' '--- NetworkManager ---' >&2
  journalctl -u NetworkManager.service -b --no-pager -n 80 >&2 || true
  printf '%s\n' '--- wpa_supplicant ---' >&2
  systemctl --no-pager --full status wpa_supplicant.service >&2 || true
  journalctl -u wpa_supplicant.service -b --no-pager -n 80 >&2 || true
  exit 1
}

for command in nmcli ip iw rfkill ss awk grep tr tail systemctl journalctl; do
  command -v "$command" >/dev/null 2>&1 || fail "required command missing: $command"
done

install -d -o growcentral -g growcentral -m 0750 "$STATE_DIR"
install -d -o root -g growcentral -m 0750 "$CERT_DIR"

# The CI image smoke test runs in a container without Raspberry Pi radio hardware.
if systemd-detect-virt --quiet --container; then
  log "Container smoke boot detected; skipping physical Wi-Fi setup."
  exit 0
fi

MODEL="$(tr -d '\000' </proc/device-tree/model 2>/dev/null || true)"
case "$MODEL" in
  *"Raspberry Pi 3 Model B Plus"*) PLATFORM="pi3b+"; EXPECTED_SOC="BCM2837B0"; AP_WAIT=55 ;;
  *"Raspberry Pi 3 Model B"*) PLATFORM="pi3b"; EXPECTED_SOC="BCM2837"; AP_WAIT=60 ;;
  *"Raspberry Pi 400"*) PLATFORM="pi400"; EXPECTED_SOC="BCM2711"; AP_WAIT=45 ;;
  *"Raspberry Pi 4 Model B"*) PLATFORM="pi4b"; EXPECTED_SOC="BCM2711"; AP_WAIT=45 ;;
  *"Raspberry Pi 5 Model B"*) PLATFORM="pi5"; EXPECTED_SOC="BCM2712"; AP_WAIT=45 ;;
  *"Raspberry Pi Compute Module 5"*) PLATFORM="cm5"; EXPECTED_SOC="BCM2712"; AP_WAIT=50 ;;
  *"Raspberry Pi Compute Module 4"*) PLATFORM="cm4"; EXPECTED_SOC="BCM2711"; AP_WAIT=50 ;;
  *"Raspberry Pi Compute Module 3"*) PLATFORM="cm3"; EXPECTED_SOC="BCM2837"; AP_WAIT=60 ;;
  *"Raspberry Pi"*) PLATFORM="raspberrypi"; EXPECTED_SOC="unknown"; AP_WAIT=60 ;;
  *) PLATFORM="unknown"; EXPECTED_SOC="unknown"; AP_WAIT=60 ;;
esac

systemctl is-active --quiet NetworkManager.service || systemctl start NetworkManager.service

# Keep wlan0 when present (confirmed Pi 3B/4 path), otherwise accept the first
# Wi-Fi device NetworkManager manages (USB Wi-Fi or Compute Module carrier).
for _ in $(seq 1 40); do
  WIFI_DEVICES="$(nmcli -t -e yes -f DEVICE,TYPE device status 2>/dev/null | awk -F: '$2 == "wifi" {print $1}')"
  if printf '%s\n' "$WIFI_DEVICES" | grep -Fxq wlan0; then WLAN=wlan0; break; fi
  WLAN="$(printf '%s\n' "$WIFI_DEVICES" | awk 'NF {print; exit}')"
  [ -n "$WLAN" ] && break
  sleep 1
done
[ -n "$WLAN" ] || fail "no NetworkManager Wi-Fi device appeared within 40 seconds"

log "Hardware model=${MODEL:-unknown} profile=${PLATFORM} expected_soc=${EXPECTED_SOC} wlan=${WLAN} ap_wait=${AP_WAIT}s"
printf '%s\n' "${MODEL:-unknown}" >"${STATE_DIR}/hardware-model"
printf '%s\n' "$PLATFORM" >"${STATE_DIR}/hardware-profile"
printf '%s\n' "$WLAN" >"${STATE_DIR}/hardware-wlan-interface"
chown growcentral:growcentral "$STATE_DIR/hardware-model" "$STATE_DIR/hardware-profile" "$STATE_DIR/hardware-wlan-interface" || true
chmod 0640 "$STATE_DIR/hardware-model" "$STATE_DIR/hardware-profile" "$STATE_DIR/hardware-wlan-interface" || true

# If the configured home WLAN is already active, do not steal it for AP use.
if nmcli -t -f NAME,DEVICE connection show --active | grep -Fxq "grow-central-uplink:${WLAN}"; then
  log "Home WLAN is already active on ${WLAN}; setup AP is not required."
  exit 0
fi

rfkill unblock wifi || true
nmcli radio wifi on
iw reg set "$REGDOMAIN" || true

for _ in $(seq 1 40); do
  [ -e "/sys/class/net/${WLAN}" ] && break
  sleep 1
done
[ -e "/sys/class/net/${WLAN}" ] || fail "${WLAN} did not appear within 40 seconds"

nmcli device set "$WLAN" managed yes || true
ip link set dev "$WLAN" up || true

for _ in $(seq 1 30); do
  DEVICE_TYPE="$(nmcli -g GENERAL.TYPE device show "$WLAN" 2>/dev/null || true)"
  [ "$DEVICE_TYPE" = "wifi" ] && break
  sleep 1
done
[ "$(nmcli -g GENERAL.TYPE device show "$WLAN" 2>/dev/null || true)" = "wifi" ] || fail "NetworkManager does not expose ${WLAN} as Wi-Fi"

if ! iw list 2>/dev/null | grep -Eq '^[[:space:]]*\*[[:space:]]+AP([[:space:]]|$)'; then
  fail "Wi-Fi driver does not advertise AP mode"
fi

MAC="$(cat "/sys/class/net/${WLAN}/address" 2>/dev/null || true)"
[ -n "$MAC" ] || fail "could not read ${WLAN} MAC address"
MAC_SUFFIX="$(printf '%s' "$MAC" | tr -d ':' | tail -c 5 | tr '[:lower:]' '[:upper:]')"
SSID="135er-GrowCentral-Setup-${MAC_SUFFIX}"

create_ap_profile() {
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

  nmcli -f connection.interface-name,802-11-wireless.mode,802-11-wireless.band,802-11-wireless.channel,ipv4.method,ipv4.addresses connection show "$CONNECTION" >/dev/null \
    || fail "NetworkManager rejected the setup AP profile"
}

reset_wifi_soft() {
  log "Resetting ${WLAN} before AP retry."
  nmcli connection down "$CONNECTION" >/dev/null 2>&1 || true
  nmcli device disconnect "$WLAN" >/dev/null 2>&1 || true
  rfkill unblock wifi || true
  nmcli radio wifi off || true
  sleep 2
  nmcli radio wifi on || true
  iw reg set "$REGDOMAIN" || true
  nmcli device set "$WLAN" managed yes >/dev/null 2>&1 || true
  ip link set dev "$WLAN" up >/dev/null 2>&1 || true
  sleep 4
}

recover_supplicant_and_networkmanager() {
  log "Recovering Wi-Fi control path after supplicant timeout."
  nmcli connection down "$CONNECTION" >/dev/null 2>&1 || true
  nmcli device disconnect "$WLAN" >/dev/null 2>&1 || true

  # Raspberry Pi OS normally exposes wpa_supplicant through D-Bus. Restarting
  # the service is safe here because this is still the unprovisioned first boot.
  if systemctl list-unit-files wpa_supplicant.service >/dev/null 2>&1; then
    systemctl restart wpa_supplicant.service || true
    sleep 3
  fi

  systemctl restart NetworkManager.service
  for _ in $(seq 1 30); do
    systemctl is-active --quiet NetworkManager.service && \
      nmcli -t -e yes -f DEVICE,TYPE device status 2>/dev/null | awk -F: -v dev="$WLAN" '$1 == dev && $2 == "wifi" {found=1} END {exit !found}' && break
    sleep 1
  done

  systemctl is-active --quiet NetworkManager.service || fail "NetworkManager did not recover"
  nmcli device set "$WLAN" managed yes >/dev/null 2>&1 || true
  rfkill unblock wifi || true
  nmcli radio wifi on || true
  iw reg set "$REGDOMAIN" || true
  ip link set dev "$WLAN" up >/dev/null 2>&1 || true
  sleep 4
}

activate_ap() {
  local wait_seconds="$1"
  nmcli --wait "$wait_seconds" connection up "$CONNECTION"
}

create_ap_profile

if ! activate_ap "$AP_WAIT"; then
  log "AP activation failed (possible supplicant-timeout); starting soft radio recovery."
  reset_wifi_soft
  create_ap_profile

  if ! activate_ap "$AP_WAIT"; then
    log "Second AP activation failed; restarting supplicant/NetworkManager control path once."
    recover_supplicant_and_networkmanager
    create_ap_profile
    activate_ap "$AP_WAIT" || fail "NetworkManager could not activate the setup AP after supplicant recovery"
  fi
fi

for _ in $(seq 1 35); do
  if ip -4 address show dev "$WLAN" | grep -Fq "$ADDRESS" \
    && ss -H -lun | awk '$4 ~ /:67$/ { found=1 } END { exit !found }'; then
    log "READY: model=${MODEL:-unknown} profile=${PLATFORM} interface=${WLAN} SSID=${SSID} ADDRESS=${ADDRESS} DHCP=${DHCP_RANGE}"
    exit 0
  fi
  sleep 1
done

fail "Setup AP did not acquire ${ADDRESS} with an active DHCP listener"
