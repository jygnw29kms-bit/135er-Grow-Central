#!/usr/bin/env bash
# Testimage-only controller for an outbound reverse-SSH maintenance tunnel.
set -Eeuo pipefail

SERVICE="grow-central-remote-maintenance.service"
STATE_DIR="/var/lib/135er-grow-central/remote-maintenance"
KEY_FILE="${STATE_DIR}/id_ed25519"
KNOWN_HOSTS="${STATE_DIR}/known_hosts"
CONFIG="/etc/135er-grow-central/remote-maintenance.conf"
CLOUD_URL="${GC_MAINTENANCE_CLOUD_URL:-https://135ercloud.dezender.de}"

die() { echo "FEHLER: $*" >&2; exit 1; }
need_root() { [[ ${EUID:-$(id -u)} -eq 0 ]] || die "Bitte mit sudo ausführen."; }
valid_name() { [[ "$1" =~ ^[A-Za-z0-9._-]+$ ]]; }

init_key() {
  need_root
  install -d -o growcentral -g growcentral -m 0700 "$STATE_DIR"
  if [[ ! -f "$KEY_FILE" ]]; then
    runuser -u growcentral -- ssh-keygen -q -t ed25519 -N '' -C "growcentral-test-$(hostname)" -f "$KEY_FILE"
  fi
  chmod 0600 "$KEY_FILE"
  chmod 0644 "${KEY_FILE}.pub"
  echo "Öffentlicher Pi-Schlüssel (auf dem VPS beim Tunnel-Benutzer hinterlegen):"
  cat "${KEY_FILE}.pub"
}

configure() {
  need_root
  local host="${1:-}" user="${2:-}" remote_port="${3:-}" expected_fingerprint="${4:-}"
  valid_name "$host" || die "Ungültiger VPS-Hostname."
  valid_name "$user" || die "Ungültiger VPS-Benutzer."
  [[ "$remote_port" =~ ^[0-9]+$ ]] && (( remote_port >= 1024 && remote_port <= 65535 )) \
    || die "Remote-Port muss zwischen 1024 und 65535 liegen."
  [[ "$expected_fingerprint" =~ ^SHA256:[A-Za-z0-9+/]+$ ]] || die "SSH-Host-Fingerprint im Format SHA256:... erforderlich."

  init_key >/dev/null
  local scan actual
  scan="$(ssh-keyscan -T 10 -t ed25519 "$host" 2>/dev/null)" || die "VPS-Host-Key nicht abrufbar."
  [[ -n "$scan" ]] || die "VPS liefert keinen Ed25519-Host-Key."
  actual="$(ssh-keygen -E sha256 -lf /dev/stdin <<<"$scan" | awk 'NR==1{print $2}')"
  [[ "$actual" == "$expected_fingerprint" ]] || die "Host-Key falsch: erhalten $actual"

  printf '%s\n' "$scan" >"$KNOWN_HOSTS"
  chown growcentral:growcentral "$KNOWN_HOSTS"
  chmod 0600 "$KNOWN_HOSTS"
  cat >"$CONFIG" <<EOF
GC_REMOTE_MAINTENANCE_HOST=$host
GC_REMOTE_MAINTENANCE_USER=$user
GC_REMOTE_MAINTENANCE_PORT=$remote_port
EOF
  chown root:growcentral "$CONFIG"
  chmod 0640 "$CONFIG"
  echo "Konfiguration gespeichert. Aktivierung: sudo $0 enable"
}

enable_tunnel() {
  need_root
  [[ -s "$CONFIG" && -s "$KEY_FILE" && -s "$KNOWN_HOSTS" ]] || die "Zuerst init/configure ausführen."
  systemctl enable --now "$SERVICE"
  systemctl --no-pager -l status "$SERVICE"
}

enroll() {
  need_root
  local activation_code="${1:-}" request response request_id request_token status deadline
  if [[ "$activation_code" == "-" ]]; then
    IFS= read -r activation_code
  fi
  [[ "$activation_code" =~ ^GC-[A-Z2-9]{6}-[A-Z2-9]{6}$ ]] || die "Ungültiger Aktivierungscode."
  init_key >/dev/null
  request="$(jq -n --arg code "$activation_code" --arg key "$(cat "${KEY_FILE}.pub")" --arg name "$(hostname)" \
    '{activation_code:$code,public_key:$key,hostname:$name}')"
  response="$(printf '%s' "$request" | curl --fail --silent --show-error --max-time 20 -H 'Content-Type: application/json' \
    --data-binary @- "$CLOUD_URL/api/v2/maintenance/enroll")" || die "Cloud-Enrollment nicht erreichbar."
  activation_code=""; request=""
  request_id="$(jq -er '.request_id' <<<"$response")" || die "Ungültige Cloud-Antwort."
  request_token="$(jq -er '.request_token' <<<"$response")" || die "Ungültige Cloud-Antwort."
  deadline=$((SECONDS + 90))
  while (( SECONDS < deadline )); do
    sleep 2
    response="$(curl --fail --silent --show-error --max-time 15 \
      -H "Authorization: Bearer $request_token" "$CLOUD_URL/api/v2/maintenance/enroll/$request_id")" || continue
    status="$(jq -r '.status // ""' <<<"$response")"
    case "$status" in
      approved)
        configure "$(jq -er '.host' <<<"$response")" "$(jq -er '.user' <<<"$response")" \
          "$(jq -er '.port' <<<"$response")" "$(jq -er '.fingerprint' <<<"$response")" >/dev/null
        request_token=""; response=""
        systemctl enable --now "$SERVICE"
        systemctl is-active --quiet "$SERVICE" || die "Fernwartungsdienst konnte nicht gestartet werden."
        echo "Fernwartung sicher aktiviert."
        return 0
        ;;
      rejected) die "Aktivierungscode abgelehnt oder abgelaufen." ;;
    esac
  done
  die "Zeitüberschreitung beim Cloud-Enrollment."
}

disable_tunnel() {
  need_root
  systemctl disable --now "$SERVICE" 2>/dev/null || true
  echo "Fernwartung deaktiviert. Schlüssel und Konfiguration bleiben lokal erhalten."
}

status_tunnel() {
  systemctl --no-pager -l status "$SERVICE" || true
  [[ -f "$CONFIG" ]] && sed -E 's/=.*/=[gesetzt]/' "$CONFIG" || true
}

case "${1:-}" in
  init) init_key ;;
  show-key) [[ -f "${KEY_FILE}.pub" ]] || init_key >/dev/null; cat "${KEY_FILE}.pub" ;;
  configure) shift; configure "$@" ;;
  enroll) shift; enroll "$@" ;;
  enable) enable_tunnel ;;
  disable) disable_tunnel ;;
  status) status_tunnel ;;
  *)
    echo "Verwendung: sudo $0 {enroll EINMALCODE|init|show-key|configure HOST USER REMOTE_PORT SHA256:FINGERPRINT|enable|disable|status}"
    exit 2
    ;;
esac
