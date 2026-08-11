#!/usr/bin/env bash
set -euo pipefail

CONNECTION="grow-central-setup-ap"
ADDRESS="10.42.0.1/24"
STATE_DIR="/var/lib/135er-grow-central"
CERT_DIR="/etc/135er-grow-central"

install -d -o growcentral -g growcentral -m 0750 "$STATE_DIR"
install -d -o root -g growcentral -m 0750 "$CERT_DIR"

if [[ ! -s "$CERT_DIR/setup-portal.key" || ! -s "$CERT_DIR/setup-portal.crt" ]]; then
  openssl req -x509 -newkey rsa:3072 -sha256 -nodes -days 3650 \
    -subj "/CN=135er-Grow-Central-Setup" \
    -addext "subjectAltName=IP:10.42.0.1,DNS:grow-central.setup" \
    -keyout "$CERT_DIR/setup-portal.key" -out "$CERT_DIR/setup-portal.crt"
  chmod 0600 "$CERT_DIR/setup-portal.key"
  chmod 0644 "$CERT_DIR/setup-portal.crt"
fi

nmcli radio wifi on
if ! nmcli -t -f NAME connection show | grep -Fxq "$CONNECTION"; then
  MAC_SUFFIX="$(cat /sys/class/net/wlan0/address | tr -d ':' | tail -c 5 | tr '[:lower:]' '[:upper:]')"
  nmcli connection add type wifi ifname wlan0 con-name "$CONNECTION" ssid "135er-GrowCentral-Setup-${MAC_SUFFIX}"
fi

# Apply the complete profile on every start. This deliberately repairs an
# existing profile left incomplete by an interrupted first boot.
nmcli connection modify "$CONNECTION" \
  connection.interface-name wlan0 \
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
  ipv4.never-default yes \
  ipv4.ignore-auto-dns yes \
  ipv6.method shared \
  ipv6.never-default yes

nmcli connection down "$CONNECTION" >/dev/null 2>&1 || true
nmcli --wait 30 connection up "$CONNECTION"

# Do not start the portal until the AP really owns its documented IPv4
# address. NetworkManager's shared mode then serves DHCP to setup clients.
for _ in {1..20}; do
  if ip -4 address show dev wlan0 | grep -Fq "10.42.0.1/24"; then
    exit 0
  fi
  sleep 1
done

echo "Setup access point did not acquire ${ADDRESS}" >&2
exit 1
