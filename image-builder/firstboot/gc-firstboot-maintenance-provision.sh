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

# Private operator images may carry a fixed *password hash* for test access.
# No plaintext password is present in the image or this script. The private
# builder is the only authorized source of this hash; public builds omit it.
HASH_FILE=/etc/135er-grow-central/operator-maint-password.hash
if [[ -f "$HASH_FILE" ]]; then
  [[ ! -L "$HASH_FILE" && "$(stat -c %a "$HASH_FILE")" == 600 ]] || {
    echo "Invalid operator password-hash permissions" >&2; exit 1;
  }
  password_hash="$(cat "$HASH_FILE")"
  if [[ ! "$password_hash" =~ ^\$6\$[A-Za-z0-9./$]{30,200}$ ]]; then
    echo "Invalid SHA512-crypt maintenance hash" >&2; exit 1;
  fi
  usermod --password "$password_hash" gc-maint
  unset password_hash
  # Main config is appended at its end, so all normal users retain the
  # key-only global policy. Match User overrides only gc-maint.
  SSH_CONFIG=/etc/ssh/sshd_config
  MARKER="# GC_OPERATOR_TEST_PASSWORD_gc-maint"
  if ! grep -Fqx "$MARKER" "$SSH_CONFIG"; then
    cat >>"$SSH_CONFIG" <<'SSHCONF'

# GC_OPERATOR_TEST_PASSWORD_gc-maint
Match User gc-maint
    PasswordAuthentication yes
    KbdInteractiveAuthentication no
    PubkeyAuthentication yes
SSHCONF
  fi
  /usr/sbin/sshd -t
  actual="$(/usr/sbin/sshd -T -C user=gc-maint,host=localhost,addr=127.0.0.1 | awk '$1=="passwordauthentication" {print $2; exit}')"
  [[ "$actual" == yes ]] || { echo "SSH gc-maint password access not enabled" >&2; exit 1; }
  systemctl reload ssh.service
  rm -f -- "$HASH_FILE"
  echo "Operator test password enabled for gc-maint only."
fi
# Delete only after successful installation, never lose the key on failure.
rm -f -- "$KEY"
echo "First-boot owner key applied; verify separate remote SSH login."
