#!/bin/bash
set -euo pipefail

USER_NAME="touranradio"
GROUP_NAME="touranradio"
CHROOT="/srv/touranradio"
INBOX="$CHROOT/upload/inbox"
TARGET="/var/www/vhosts/dezender.de/private/touran-logs"

if [ "${EUID}" -ne 0 ]; then
  echo "Run as root" >&2
  exit 1
fi

getent group "$GROUP_NAME" >/dev/null || groupadd --system "$GROUP_NAME"
id "$USER_NAME" >/dev/null 2>&1 || useradd --system --gid "$GROUP_NAME" --home /upload --shell /usr/sbin/nologin "$USER_NAME"

mkdir -p "$INBOX" "$TARGET"
# Chroot path itself must be root-owned and not writable by the SFTP user.
chown root:root "$CHROOT" "$CHROOT/upload"
chmod 0755 "$CHROOT" "$CHROOT/upload"
chown "$USER_NAME:$GROUP_NAME" "$INBOX"
chmod 0730 "$INBOX"
# Plesk PHP-FPM normally runs as the subscription system user, not necessarily www-data.
# Match the private log store to the actual webspace owner so PHP can write uploads.
WEB_OWNER="$(stat -c '%U' /var/www/vhosts/dezender.de/httpdocs)"
WEB_GROUP="$(stat -c '%G' /var/www/vhosts/dezender.de/httpdocs)"
chown "$WEB_OWNER:$WEB_GROUP" "$TARGET"
chmod 0770 "$TARGET"

KEY_DIR="/etc/ssh/authorized_keys"
mkdir -p "$KEY_DIR"
chown root:root "$KEY_DIR"
chmod 0755 "$KEY_DIR"
AUTH_KEYS="$KEY_DIR/$USER_NAME"
touch "$AUTH_KEYS"
chown root:root "$AUTH_KEYS"
chmod 0644 "$AUTH_KEYS"

CFG="/etc/ssh/sshd_config.d/90-touranradio-sftp.conf"
cat > "$CFG" <<'EOF'
Match User touranradio
    ChrootDirectory /srv/touranradio
    ForceCommand internal-sftp -d /upload/inbox -u 007
    PasswordAuthentication no
    KbdInteractiveAuthentication no
    PubkeyAuthentication yes
    AuthorizedKeysFile /etc/ssh/authorized_keys/%u
    PermitTTY no
    X11Forwarding no
    AllowTcpForwarding no
    PermitTunnel no
    GatewayPorts no
EOF

sshd -t
systemctl reload ssh || systemctl reload sshd

echo "touranradio SFTP sandbox ready."
echo "Add the RADIO PUBLIC KEY to: $AUTH_KEYS"
echo "SFTP target seen by radio: /upload/inbox"
echo "Server-side inbox: $INBOX"
echo "Private analysis store: $TARGET"
