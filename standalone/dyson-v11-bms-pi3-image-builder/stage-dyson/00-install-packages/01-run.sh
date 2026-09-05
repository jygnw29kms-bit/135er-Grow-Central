#!/usr/bin/env bash
set -e
install -d /opt/dyson-bms
install -m 0755 files/app.py /opt/dyson-bms/app.py
install -m 0644 files/dyson-bms-ui.service /etc/systemd/system/dyson-bms-ui.service
systemctl enable dyson-bms-ui.service
cat >/etc/default/dyson-bms <<'EOF'
CAN_IFACE=can0
CAN_BITRATE=500000
EOF
if ! grep -q '^dtparam=spi=on' /boot/firmware/config.txt 2>/dev/null; then
  echo 'dtparam=spi=on' >> /boot/firmware/config.txt
fi
