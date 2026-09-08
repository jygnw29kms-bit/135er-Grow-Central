#!/usr/bin/env bash
set -euo pipefail

PACKAGE_VERSION="0.3.0-1"
PACKAGE_FILE="dyson-v11-bms_${PACKAGE_VERSION}_all.deb"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd)"
APP_SOURCE="${REPO_ROOT}/standalone/dyson-v11-bms-pi3-image-builder/stage-dyson/00-install-packages/files/app.py"
OUTPUT_DIR="${1:-${SCRIPT_DIR}/dist}"

test -f "${APP_SOURCE}"
grep -q '^APP_VERSION = "0.3.0"$' "${APP_SOURCE}"
install -d -m 0755 "${OUTPUT_DIR}"

PACKAGE_ROOT="$(mktemp -d)"
chmod 0755 "${PACKAGE_ROOT}"
cleanup() {
  case "${PACKAGE_ROOT}" in
    /tmp/*) rm -rf -- "${PACKAGE_ROOT}" ;;
    *) echo "Unerwarteter temporärer Pfad: ${PACKAGE_ROOT}" >&2; exit 1 ;;
  esac
}
trap cleanup EXIT

install -d -m 0755 \
  "${PACKAGE_ROOT}/DEBIAN" \
  "${PACKAGE_ROOT}/opt/dyson-v11-bms" \
  "${PACKAGE_ROOT}/usr/bin" \
  "${PACKAGE_ROOT}/lib/systemd/system"
install -m 0755 "${APP_SOURCE}" "${PACKAGE_ROOT}/opt/dyson-v11-bms/app.py"

cat > "${PACKAGE_ROOT}/DEBIAN/control" <<EOF
Package: dyson-v11-bms
Version: ${PACKAGE_VERSION}
Section: utils
Priority: optional
Architecture: all
Maintainer: 135er Service Center
Depends: python3, python3-flask, can-utils, iproute2, openocd, git, cmake, make, gcc-arm-none-eabi
Homepage: https://dezender.de/dyson-v11-bms/
Description: Dyson V11 BMS service and layered diagnostic interface
 Validates real Dyson UART responses, diagnoses adapter and protocol failures,
 and provides optional SocketCAN and SWD tooling for Raspberry Pi systems.
EOF

cat > "${PACKAGE_ROOT}/lib/systemd/system/dyson-v11-bms.service" <<'EOF'
[Unit]
Description=135er Dyson V11 BMS Service Center
After=network-online.target
Wants=network-online.target

[Service]
Type=simple
EnvironmentFile=-/etc/default/dyson-v11-bms
Environment=PYTHONUNBUFFERED=1
ExecStart=/usr/bin/python3 /opt/dyson-v11-bms/app.py
Restart=always
RestartSec=3
AmbientCapabilities=CAP_NET_ADMIN CAP_NET_RAW
CapabilityBoundingSet=CAP_NET_ADMIN CAP_NET_RAW
NoNewPrivileges=true
ProtectSystem=full
ProtectHome=true
PrivateTmp=true
ReadWritePaths=/etc/default

[Install]
WantedBy=multi-user.target
EOF

cat > "${PACKAGE_ROOT}/usr/bin/dyson-v11-bms-status" <<'EOF'
#!/bin/sh
set -eu
systemctl --no-pager --full status dyson-v11-bms.service || true
echo
echo "Diagnose: http://$(hostname -I 2>/dev/null | awk '{print $1}'):8080/"
echo "API:      http://127.0.0.1:8080/api/diagnostics"
EOF
chmod 0755 "${PACKAGE_ROOT}/usr/bin/dyson-v11-bms-status"

cat > "${PACKAGE_ROOT}/DEBIAN/postinst" <<'EOF'
#!/bin/sh
set -eu

config=/etc/default/dyson-v11-bms
touch "$config"
ensure_setting() {
  key="$1"
  value="$2"
  if ! grep -q "^${key}=" "$config"; then
    printf '%s=%s\n' "$key" "$value" >> "$config"
  fi
}

ensure_setting CAN_IFACE can0
ensure_setting CAN_BITRATE 500000
ensure_setting SERIAL_DEVICE auto
ensure_setting SERIAL_BAUD 115200
ensure_setting DETECTION_TIMEOUT 5
ensure_setting AUTO_SCAN_DWELL 2.5
ensure_setting WEB_PORT 8080
chmod 0644 "$config"

if command -v systemctl >/dev/null 2>&1; then
  systemctl daemon-reload || true
  systemctl enable dyson-v11-bms.service >/dev/null 2>&1 || true
  if [ -d /run/systemd/system ]; then
    systemctl restart dyson-v11-bms.service
  fi
fi
EOF
chmod 0755 "${PACKAGE_ROOT}/DEBIAN/postinst"

cat > "${PACKAGE_ROOT}/DEBIAN/prerm" <<'EOF'
#!/bin/sh
set -eu
if [ "${1:-}" = remove ] && command -v systemctl >/dev/null 2>&1; then
  systemctl disable --now dyson-v11-bms.service >/dev/null 2>&1 || true
fi
EOF
chmod 0755 "${PACKAGE_ROOT}/DEBIAN/prerm"

cat > "${PACKAGE_ROOT}/DEBIAN/postrm" <<'EOF'
#!/bin/sh
set -eu
if [ "${1:-}" = purge ]; then
  rm -f /etc/default/dyson-v11-bms
fi
if command -v systemctl >/dev/null 2>&1; then
  systemctl daemon-reload || true
fi
EOF
chmod 0755 "${PACKAGE_ROOT}/DEBIAN/postrm"

dpkg-deb --root-owner-group --build "${PACKAGE_ROOT}" "${OUTPUT_DIR}/${PACKAGE_FILE}"
sha256sum "${OUTPUT_DIR}/${PACKAGE_FILE}"
