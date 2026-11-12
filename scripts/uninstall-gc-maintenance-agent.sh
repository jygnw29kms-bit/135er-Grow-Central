#!/usr/bin/env bash
# Remove ONLY the maintenance pieces installed by install-gc-maintenance-agent.sh.
set -Eeuo pipefail
if [[ $EUID -ne 0 ]]; then echo "Run with sudo" >&2; exit 1; fi
systemctl disable --now gc-maintenance-ssh-check.timer 2>/dev/null || true
rm -f /etc/systemd/system/gc-maintenance-ssh-check.timer
rm -f /etc/systemd/system/gc-maintenance-ssh-check.service
rm -f /usr/local/sbin/gc-maintenance-ssh-check
rm -f /etc/sudoers.d/90-growcentral-maintenance
systemctl daemon-reload
echo "Maintenance watchdog and sudo privilege removed."
echo "Maintenance account and its authorized_keys intentionally retained for forensic review."
echo "To revoke a specific public key, manually inspect the account's authorized_keys."
echo "No SSH service, firewall, user data, or other accounts were changed."
