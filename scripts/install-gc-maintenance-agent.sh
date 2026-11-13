#!/usr/bin/env bash
# Grow Central Pi: opt-in, SSH-key-only maintenance account and watchdog.
# Does not embed secrets, enroll with a third-party service, or expose new ports.
set -Eeuo pipefail
umask 077
USER_NAME="gc-maint"
PUBLIC_KEY_FILE=""
while (($#)); do
  case "$1" in
    --public-key-file) PUBLIC_KEY_FILE="${2:?missing public key path}"; shift 2 ;;
    --user) USER_NAME="${2:?missing account name}"; shift 2 ;;
    *) echo "Unknown parameter: $1" >&2; exit 2 ;;
  esac
done
if [[ $EUID -ne 0 ]]; then echo "Run as root: sudo bash $0 --public-key-file /path/to/publickey.pub" >&2; exit 1; fi
if [[ ! "$USER_NAME" =~ ^[a-z_][a-z0-9_-]{2,29}$ ]]; then echo "Invalid user name" >&2; exit 2; fi
if [[ -z "$PUBLIC_KEY_FILE" || ! -f "$PUBLIC_KEY_FILE" ]]; then echo "Explicit public key file required" >&2; exit 2; fi
if ! command -v sshd >/dev/null 2>&1 && [[ ! -x /usr/sbin/sshd ]]; then echo "openssh-server is required; no SSH package changes performed" >&2; exit 1; fi
if ! command -v systemctl >/dev/null || ! command -v visudo >/dev/null; then echo "systemd and sudo required" >&2; exit 1; fi

# A single complete, locally provisioned public key. Never accept a private key.
pub="$(head -n 1 "$PUBLIC_KEY_FILE" | tr -d '\r')"
if [[ "$pub" != ssh-ed25519\ * && "$pub" != ecdsa-sha2-nistp256\ * && "$pub" != ssh-rsa\ * ]]; then
  echo "Expected a single OpenSSH public key" >&2; exit 2
fi
if [[ "$(wc -l < "$PUBLIC_KEY_FILE")" -gt 1 ]]; then echo "Provide exactly one public key" >&2; exit 2; fi
keytype="${pub%% *}"
keydata="${pub#* }"; keydata="${keydata%% *}"
if [[ ! "$keydata" =~ ^[A-Za-z0-9+/]+={0,2}$ || ${#keydata} -lt 40 ]]; then echo "Malformed public key" >&2; exit 2; fi
if command -v ssh-keygen >/dev/null; then
  tempkey="$(mktemp)"; trap 'rm -f "$tempkey"' EXIT
  printf '%s %s\n' "$keytype" "$keydata" > "$tempkey"
  ssh-keygen -lf "$tempkey" >/dev/null || { echo "Public key rejected by ssh-keygen" >&2; exit 2; }
fi

if ! getent passwd "$USER_NAME" >/dev/null; then
  useradd --create-home --user-group --shell /bin/bash "$USER_NAME"
fi
userhome="$(getent passwd "$USER_NAME" | cut -d: -f6)"
if [[ -z "$userhome" || "$userhome" == "/" ]]; then echo "Unsafe account home" >&2; exit 1; fi
install -d -m 0700 -o "$USER_NAME" -g "$(id -gn "$USER_NAME")" "$userhome/.ssh"
# Key options restrict agent/X forwarding, but retain PTY and SSH tunnel support.
auth="$userhome/.ssh/authorized_keys"
touch "$auth"
chmod 0600 "$auth"
chown "$USER_NAME:$(id -gn "$USER_NAME")" "$auth"
entry="restrict,pty,port-forwarding $keytype $keydata"
if ! grep -Fqx "$entry" "$auth"; then
  printf '%s\n' "$entry" >> "$auth"
fi
# No password login for this account. Existing users' auth remains untouched.
passwd --lock "$USER_NAME" >/dev/null
chmod 0600 "$auth"
chown "$USER_NAME:$(id -gn "$USER_NAME")" "$auth"

sudo_file="/etc/sudoers.d/90-growcentral-maintenance"
printf '%s ALL=(ALL:ALL) NOPASSWD: ALL\n' "$USER_NAME" > "$sudo_file"
chmod 0440 "$sudo_file"
if ! visudo -cf "$sudo_file" >/dev/null; then
  rm -f "$sudo_file"
  echo "sudoers validation failed; privilege file removed" >&2; exit 1
fi

# A sudoers file alone is not proof that this session can gain privileges.
# Fail first boot if NoNewPrivileges or a broken sudo policy prevents actual root.
if ! command -v runuser >/dev/null 2>&1; then
  echo "runuser is required to verify administrative access" >&2; exit 1
fi
verified_uid="$(runuser -u "$USER_NAME" -- sudo -n /usr/bin/id -u 2>/dev/null || true)"
if [[ "$verified_uid" != 0 ]]; then
  echo "Maintenance sudo verification failed: expected root UID 0" >&2
  exit 1
fi
printf 'MAINTENANCE_SUDO_VERIFIED=UID_0\\n'


# SSH key access requires that existing sshd config already allows key auth.
# We deliberately do not overwrite sshd_config, firewall, or other services.
if [[ -x /usr/sbin/sshd ]]; then /usr/sbin/sshd -t; else sshd -t; fi
service="ssh"
if ! systemctl cat ssh.service >/dev/null 2>&1; then service="sshd"; fi
systemctl enable --now "$service.service"

cat >/usr/local/sbin/gc-maintenance-ssh-check <<'CHECK'
#!/usr/bin/env bash
set -Eeuo pipefail
service=ssh
if ! systemctl cat ssh.service >/dev/null 2>&1; then service=sshd; fi
if ! systemctl is-active --quiet "$service.service"; then
  logger -t gc-maintenance "SSH unavailable, attempting systemd start"
  systemctl start "$service.service"
fi
CHECK
chmod 0700 /usr/local/sbin/gc-maintenance-ssh-check
cat >/etc/systemd/system/gc-maintenance-ssh-check.service <<'UNIT'
[Unit]
Description=Grow Central SSH maintenance availability check
After=network.target
[Service]
Type=oneshot
ExecStart=/usr/local/sbin/gc-maintenance-ssh-check
User=root
NoNewPrivileges=yes
UNIT
cat >/etc/systemd/system/gc-maintenance-ssh-check.timer <<'TIMER'
[Unit]
Description=Regular Grow Central SSH availability check
[Timer]
OnBootSec=45s
OnUnitInactiveSec=1min
AccuracySec=15s
Persistent=true
[Install]
WantedBy=timers.target
TIMER
systemctl daemon-reload
systemctl enable --now gc-maintenance-ssh-check.timer
systemctl start gc-maintenance-ssh-check.service
echo "INSTALLED user=$USER_NAME"
echo "SSH_SERVICE=$service"
echo "TIMER=$(systemctl is-active gc-maintenance-ssh-check.timer)"
echo "SSH_ACTIVE=$(systemctl is-active "$service.service")"
echo "SECURITY=key-only account; root/sudo full-access; no new listening port"
echo "SSH_CONNECTION_MUST_BE_VERIFIED_FROM_AN_AUTHORIZED_CLIENT"
