#!/usr/bin/env bash
# VPS-side setup for test-image reverse SSH maintenance tunnels.
set -Eeuo pipefail

TUNNEL_USER="growcentral-tunnel"
TUNNEL_HOME="/var/lib/${TUNNEL_USER}"
AUTH_KEYS="${TUNNEL_HOME}/.ssh/authorized_keys"
SSHD_DROPIN="/etc/ssh/sshd_config.d/70-growcentral-test-tunnel.conf"

die() { echo "FEHLER: $*" >&2; exit 1; }
[[ ${EUID:-$(id -u)} -eq 0 ]] || die "Bitte als root ausführen."

init_bastion() {
  if ! id "$TUNNEL_USER" >/dev/null 2>&1; then
    useradd --system --create-home --home-dir "$TUNNEL_HOME" --shell /bin/bash "$TUNNEL_USER"
  fi
  passwd -l "$TUNNEL_USER" >/dev/null
  install -d -o "$TUNNEL_USER" -g "$TUNNEL_USER" -m 0700 "${TUNNEL_HOME}/.ssh"
  touch "$AUTH_KEYS"
  chown "$TUNNEL_USER:$TUNNEL_USER" "$AUTH_KEYS"
  chmod 0600 "$AUTH_KEYS"
  cat >"$SSHD_DROPIN" <<EOF
Match User $TUNNEL_USER
    PasswordAuthentication no
    KbdInteractiveAuthentication no
    PubkeyAuthentication yes
    AuthenticationMethods publickey
    AllowTcpForwarding remote
    GatewayPorts no
    X11Forwarding no
    AllowAgentForwarding no
    PermitTTY no
EOF
  sshd -t || { rm -f "$SSHD_DROPIN"; die "sshd-Konfiguration ungültig; Änderung zurückgenommen."; }
  systemctl reload ssh
  echo "Bastion-Benutzer eingerichtet: $TUNNEL_USER"
}

add_device() {
  local port="${1:-}" public_key_file="${2:-}"
  [[ "$port" =~ ^[0-9]+$ ]] && (( port >= 1024 && port <= 65535 )) || die "Port 1024-65535 erforderlich."
  [[ -r "$public_key_file" ]] || die "Öffentliche Schlüsseldatei fehlt."
  init_bastion >/dev/null
  local key
  key="$(head -n 1 "$public_key_file")"
  [[ "$key" =~ ^ssh-ed25519[[:space:]]+[A-Za-z0-9+/=]+ ]] || die "Nur Ed25519-Public-Keys erlaubt."
  grep -Fq "permitlisten=\"127.0.0.1:${port}\"" "$AUTH_KEYS" && die "Port bereits vergeben."
  printf 'restrict,port-forwarding,permitlisten="127.0.0.1:%s" %s\n' "$port" "$key" >>"$AUTH_KEYS"
  chown "$TUNNEL_USER:$TUNNEL_USER" "$AUTH_KEYS"
  chmod 0600 "$AUTH_KEYS"
  echo "Gerät hinzugefügt. Zugriff vom VPS: ssh -p $port GrowCentral@127.0.0.1"
}

remove_port() {
  local port="${1:-}"
  [[ "$port" =~ ^[0-9]+$ ]] || die "Port erforderlich."
  [[ -f "$AUTH_KEYS" ]] || return 0
  sed -i "/permitlisten=\"127\.0\.0\.1:${port}\"/d" "$AUTH_KEYS"
  echo "Port $port entfernt."
}

case "${1:-}" in
  init) init_bastion ;;
  add) shift; add_device "$@" ;;
  remove) shift; remove_port "$@" ;;
  status) id "$TUNNEL_USER"; sed -E 's#(ssh-ed25519 )[A-Za-z0-9+/=]+#\1[PUBLIC-KEY]#' "$AUTH_KEYS" 2>/dev/null || true ;;
  *) echo "Verwendung: sudo $0 {init|add PORT PUBLIC_KEY_FILE|remove PORT|status}"; exit 2 ;;
esac
