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
  nmcli connection modify "$CONNECTION" \
    802-11-wireless.mode ap \
    802-11-wireless.band bg \
    wifi-sec.key-mgmt wpa-psk \
    wifi-sec.psk grow-central-test \
    ipv4.method shared \
    ipv4.addresses "$ADDRESS" \
    ipv6.method disabled \
    connection.autoconnect yes \
    connection.autoconnect-priority 100
fi

nmcli connection up "$CONNECTION"
