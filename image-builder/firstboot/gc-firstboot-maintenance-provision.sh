#!/usr/bin/env bash
# First-boot private authorization path. A public key must be explicitly placed
# on the Pi boot partition by the owner; it is never baked into the image.
set -Eeuo pipefail
umask 077
KEY=/boot/firmware/gc-maintenance.pub
INSTALLER=/opt/135er-grow-central/scripts/install-gc-maintenance-agent.sh
if [[ ! -f "$KEY" ]]; then
  echo "No owner-provisioned key: maintenance login remains unprovisioned"
  exit 0
fi
if [[ -L "$KEY" || ! -s "$KEY" || ! -f "$INSTALLER" ]]; then
  echo "Unsafe key file or missing installer" >&2
  exit 1
fi
if [[ "$(stat -c %s "$KEY")" -gt 512 ]]; then
  echo "Owner-provisioned key file too large" >&2
  exit 1
fi
bash "$INSTALLER" --public-key-file "$KEY" --user gc-maint
# Delete only after successful installation, never lose the key on failure.
rm -f -- "$KEY"
echo "First-boot owner key applied; verify separate remote SSH login."
