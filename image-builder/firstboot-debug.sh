#!/usr/bin/env bash
# Collect a redacted support bundle for 135er-Grow Central.
# Modes: --boot-watch records first boot; --snapshot captures any later problem.
set -u
set -o pipefail

APP_DIR=/opt/135er-grow-central
STATE_DIR=/var/lib/135er-grow-central
DIAG_DIR=${STATE_DIR}/support
INSTALLED_SCRIPT=/usr/local/sbin/grow-central-support-bundle
DEBUG_UNIT=/etc/systemd/system/grow-central-firstboot-debug.service
DEBUG_DONE=${STATE_DIR}/.firstboot-debug-complete
STAMP=$(date -u +%Y%m%dT%H%M%SZ)
WORK_DIR=/tmp/grow-central-support-${STAMP}-$$
LOG_FILE=${WORK_DIR}/firstboot-debug.log
SUMMARY_FILE=${WORK_DIR}/summary.txt
CALLING_USER=${SUDO_USER:-$(id -un)}
CALLING_HOME=$(getent passwd "$CALLING_USER" 2>/dev/null | cut -d: -f6)
BOOT_WATCH=0
if [[ ${1:-} == --boot-watch ]]; then
  BOOT_WATCH=1
  CALLING_USER=GrowCentral
  CALLING_HOME=$DIAG_DIR
fi
if [[ ${1:-} == --snapshot ]]; then
  CALLING_USER=GrowCentral
  CALLING_HOME=$DIAG_DIR
fi
if [[ -z "$CALLING_HOME" || ! -d "$CALLING_HOME" ]]; then
  CALLING_HOME=/tmp
fi
ARCHIVE=${CALLING_HOME}/Grow-Central-Support-${STAMP}-$$.tar.gz
WATCH_SECONDS=${GC_DEBUG_WATCH_SECONDS:-900}
MONITOR_PIDS=()
ARCHIVE_CREATED=0

if [[ ${EUID} -ne 0 ]]; then
  echo "Bitte mit sudo ausführen: sudo bash $0" >&2
  exit 1
fi

if [[ ${1:-} == --install ]]; then
  install -D -o root -g root -m 0755 "$0" "$INSTALLED_SCRIPT"
  install -d -o root -g growcentral -m 0750 "$DIAG_DIR"
  rm -f "$DEBUG_DONE"
  tee "$DEBUG_UNIT" >/dev/null <<'EOF'
[Unit]
Description=Record the complete 135er-Grow Central first-boot transition
Wants=NetworkManager.service avahi-daemon.service 135er-grow-central.service
After=NetworkManager.service
ConditionPathExists=!/var/lib/135er-grow-central/.firstboot-debug-complete

[Service]
Type=simple
ExecStart=/usr/local/sbin/grow-central-support-bundle --boot-watch
Environment=GC_DEBUG_WATCH_SECONDS=1800
TimeoutStopSec=30
KillMode=control-group
Nice=10
IOSchedulingClass=best-effort
IOSchedulingPriority=7

[Install]
WantedBy=multi-user.target
EOF
  systemctl daemon-reload
  systemctl enable grow-central-firstboot-debug.service
  echo "Installiert. Jetzt neu starten: sudo reboot"
  echo "Nach dem Setup liegt das Archiv unter: $DIAG_DIR/"
  exit 0
fi

umask 077
mkdir -p "$WORK_DIR"
exec > >(tee -a "$LOG_FILE") 2>&1

section() {
  printf '\n\n===== %s =====\n' "$1"
}

run() {
  printf '\n$'
  printf ' %q' "$@"
  printf '\n'
  "$@"
  local rc=$?
  printf '[exit=%s]\n' "$rc"
  return 0
}

run_shell() {
  printf '\n$ %s\n' "$1"
  bash -o pipefail -c "$1"
  local rc=$?
  printf '[exit=%s]\n' "$rc"
  return 0
}

stop_monitors() {
  local pid
  for pid in "${MONITOR_PIDS[@]:-}"; do
    kill "$pid" 2>/dev/null || true
    wait "$pid" 2>/dev/null || true
  done
  MONITOR_PIDS=()
}

create_archive() {
  if (( ARCHIVE_CREATED == 1 )) || [[ ! -d "$WORK_DIR" ]]; then
    return 0
  fi
  stop_monitors
  python3 - "$WORK_DIR" <<'PY'
import re
import sys
from pathlib import Path

root = Path(sys.argv[1])
patterns = [
    re.compile(r'(?i)((?:password|passwd|wifi_password|gui_password|fritz_password|psk|token|secret|authorization|cookie|set-cookie)(?:["\x27]?\s*[:=]\s*|\s+))("[^"]*"|\x27[^\x27]*\x27|[^\s,;]+)'),
    re.compile(r'(?i)(GC_(?:GUI_PASSWORD_HASH|FRITZ_PASSWORD|.*TOKEN)\s*=\s*)(.*)'),
]
for path in root.rglob('*'):
    if not path.is_file() or path.suffix not in {'.log', '.txt', '.json'}:
        continue
    try:
        text = path.read_text(encoding='utf-8', errors='replace')
        for pattern in patterns:
            text = pattern.sub(lambda match: match.group(1) + '[REDACTED]', text)
        path.write_text(text, encoding='utf-8')
    except OSError:
        pass
PY
  tar -C /tmp -czf "$ARCHIVE" "$(basename "$WORK_DIR")" 2>/dev/null || return 0
  chown "$CALLING_USER":"$(id -gn "$CALLING_USER")" "$ARCHIVE" 2>/dev/null || true
  chmod 600 "$ARCHIVE"
  if [[ ${1:-} == --boot-watch || ${1:-} == --snapshot ]]; then
    chown root:growcentral "$ARCHIVE" 2>/dev/null || true
    chmod 640 "$ARCHIVE"
  fi
  ln -sfn "$(basename "$ARCHIVE")" "$DIAG_DIR/Grow-Central-Support-latest.tar.gz" 2>/dev/null || true
  find "$DIAG_DIR" -maxdepth 1 -type f -name 'Grow-Central-Support-*.tar.gz' -printf '%T@ %p\n' 2>/dev/null \
    | sort -rn | tail -n +11 | cut -d' ' -f2- \
    | while IFS= read -r old_archive; do
        [[ -n "$old_archive" && "$old_archive" == "$DIAG_DIR"/Grow-Central-Support-*.tar.gz ]] && rm -f -- "$old_archive"
      done
  ARCHIVE_CREATED=1
}

interrupted() {
  printf '\nAufzeichnung unterbrochen; vorhandene Daten werden gesichert.\n'
  echo "Interrupted: $(date --iso-8601=seconds)" >>"$SUMMARY_FILE"
  create_archive
  echo "TEILARCHIV: $ARCHIVE"
  exit 130
}

trap interrupted INT TERM HUP

section "Collector"
echo "UTC timestamp: $(date -u --iso-8601=seconds)"
echo "Local timestamp: $(date --iso-8601=seconds)"
echo "Collector version: 1"
echo "Calling user: $CALLING_USER"

section "Operating system and hardware"
run uname -a
run cat /etc/os-release
run cat /proc/device-tree/model
run cat "$APP_DIR/BUILD"
run uptime
run timedatectl status
run hostnamectl status
run df -hT
run df -ih
run free -h
run vcgencmd get_throttled
run vcgencmd measure_temp
run vcgencmd get_mem arm
run vcgencmd get_mem gpu
run rfkill list all
run lsusb
run lsusb -t
run bluetoothctl list
run bluetoothctl show
run bluetoothctl devices
run v4l2-ctl --list-devices

section "Boot and system state"
run systemctl is-system-running
run systemctl --failed --no-pager -l
run systemd-analyze time
run systemd-analyze critical-chain 135er-grow-central.service
run last reboot -n 3
run journalctl --list-boots --no-pager
run dmesg --ctime --level=emerg,alert,crit,err,warn
run journalctl -b -1 --no-pager -o short-precise -p warning -n 500
run coredumpctl list --no-pager

section "Grow Central units"
UNITS=(
  135er-grow-central.service
  grow-central-headless-firstboot.service
  grow-central-firstboot-firewall.service
  grow-central-setup-ap.service
  grow-central-apply-setup.path
  grow-central-apply-setup.service
  grow-central-healthcheck.service
  grow-central-healthcheck.timer
  grow-central-firstboot-debug.service
  grow-central-support-bundle.service
  grow-central-support-bundle.path
  NetworkManager.service
  avahi-daemon.service
  ssh.service
)
for unit in "${UNITS[@]}"; do
  run systemctl status "$unit" --no-pager -l
  run systemctl show "$unit" --no-pager \
    -p Id -p LoadState -p ActiveState -p SubState -p UnitFileState -p Result \
    -p ExecMainCode -p ExecMainStatus -p Conditions -p ConditionResult \
    -p FragmentPath -p DropInPaths -p Triggers -p TriggeredBy
  run systemctl cat "$unit" --no-pager
done

section "Grow Central journals from this boot"
for unit in "${UNITS[@]}"; do
  run journalctl -b -u "$unit" --no-pager -o short-precise -n 500
done
run journalctl -b -p warning --no-pager -o short-precise -n 500

section "Processes and listeners"
run ps auxww
run ss -lntup
run systemctl show 135er-grow-central.service -p User -p Group -p SupplementaryGroups -p EnvironmentFiles -p ExecStart
run systemctl show 135er-grow-central.service -p NoNewPrivileges -p PrivateTmp -p ProtectSystem -p ProtectHome -p ReadWritePaths

section "Network devices and routes"
run ip -details link show
run ip -4 address show
run ip -6 address show
run ip route show table all
run ip -6 route show table all
run ip rule show
run resolvectl status
run nmcli general status
run nmcli radio all
run nmcli -f DEVICE,TYPE,STATE,CONNECTION,CON-PATH device status
run nmcli -f GENERAL,IP4,IP6,DHCP4,DHCP6 device show wlan0
run nmcli -f GENERAL,IP4,IP6,DHCP4,DHCP6 device show eth0
run nmcli -f NAME,UUID,TYPE,DEVICE,AUTOCONNECT,AUTOCONNECT-PRIORITY connection show
run nmcli --show-secrets no connection show grow-central-setup-ap
run nmcli --show-secrets no connection show grow-central-uplink
run nmcli -f IN-USE,SSID,MODE,CHAN,FREQ,RATE,SIGNAL,BARS,SECURITY device wifi list --rescan yes ifname wlan0
run iw dev
run iw reg get

section "Connectivity probes"
run ping -4 -c 2 -W 2 10.42.0.1
run getent ahostsv4 135er-grow-central.local
run getent ahostsv4 www.debian.org
run resolvectl query 135er-grow-central.local
run avahi-resolve-host-name -4 135er-grow-central.local
run curl --fail --silent --show-error --max-time 5 http://127.0.0.1:8080/api/health
run curl --fail --silent --show-error --max-time 5 http://127.0.0.1:8080/api/setup/status
run curl --silent --show-error --max-time 5 --dump-header - http://127.0.0.1:8080/
run curl --ipv4 --fail --silent --show-error --location --max-time 15 --output /dev/null https://www.debian.org/

section "Firewall"
run ufw status verbose
run nft list ruleset

section "Files, ownership and immutable state"
run namei -l "$STATE_DIR"
run ls -la "$STATE_DIR"
run stat "$STATE_DIR"
for path in \
  "$STATE_DIR/setup-last-error" \
  "$STATE_DIR/setup-last-warning" \
  "$STATE_DIR/setup-pending.json" \
  "$STATE_DIR/.provisioned" \
  "$STATE_DIR/.headless-firstboot-ready" \
  "$STATE_DIR/.firewall-initialized" \
  "$APP_DIR/.env" \
  "$APP_DIR/web/setup.html" \
  "$APP_DIR/web/index.html"; do
  if [[ -e "$path" ]]; then
    run stat "$path"
    run lsattr "$path"
  else
    echo "MISSING: $path"
  fi
done

section "Redacted setup state"
if [[ -r "$STATE_DIR/setup-last-error" ]]; then
  run sed -n 1,20p "$STATE_DIR/setup-last-error"
fi
if [[ -r "$STATE_DIR/setup-last-warning" ]]; then
  run sed -n 1,20p "$STATE_DIR/setup-last-warning"
fi
if [[ -r "$STATE_DIR/setup-pending.json" ]]; then
  python3 - "$STATE_DIR/setup-pending.json" <<'PY'
import json, sys
from pathlib import Path

secret = {"new_password", "new_password_confirm", "wifi_password", "gui_password", "gui_password_confirm", "fritz_password"}
try:
    data = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
    safe = {}
    for key, value in data.items():
        if key in secret:
            safe[key] = f"<redacted; length={len(str(value))}>"
        else:
            safe[key] = value
    print(json.dumps(safe, ensure_ascii=False, indent=2))
except Exception as error:
    print(f"Could not parse pending setup: {type(error).__name__}: {error}")
PY
else
  echo "No readable pending setup file."
fi

section "Redacted application environment"
if [[ -r "$APP_DIR/.env" ]]; then
  awk '
    /^[[:space:]]*#/ || /^[[:space:]]*$/ { print; next }
    /^[A-Za-z_][A-Za-z0-9_]*=/ {
      key=$0; sub(/=.*/, "", key); print key "=<redacted>"; next
    }
    { print "<unparsed line redacted>" }
  ' "$APP_DIR/.env"
else
  echo "Application environment is not readable."
fi

section "Installed application identity"
run cat "$APP_DIR/VERSION"
run dpkg-query -W network-manager avahi-daemon dnsmasq-base python3 bluez ufw
run "$APP_DIR/.venv/bin/pip" freeze
run sha256sum "$APP_DIR/app/firstboot.py" "$APP_DIR/image-builder/firstboot/apply_setup.py" "$APP_DIR/image-builder/firstboot/setup-ap.sh"
run sed -n 1,220p "$APP_DIR/app/firstboot.py"
run sed -n 1,360p "$APP_DIR/image-builder/firstboot/apply_setup.py"
run sed -n 1,220p "$APP_DIR/image-builder/firstboot/setup-ap.sh"
run grep -RIn --exclude=.env --exclude='*.json' --exclude='*.db' \
  -E 'setup\.html|setup-last-error|setup-pending|grow-central-uplink|www\.debian\.org' \
  "$APP_DIR/app" "$APP_DIR/image-builder" "$APP_DIR/web"

section "Application data integrity"
run find "$APP_DIR/data" -maxdepth 2 -type f -printf '%M %u:%g %s %TY-%Tm-%TdT%TH:%TM:%TS %p\n'
while IFS= read -r database; do
  run sqlite3 "$database" 'PRAGMA quick_check;'
  run sqlite3 "$database" '.schema'
done < <(find "$APP_DIR/data" -maxdepth 2 -type f -name '*.db' -print 2>/dev/null)

section "Permissions as service user"
run id growcentral
run runuser -u growcentral -- test -r "$STATE_DIR/setup-last-error"
run runuser -u growcentral -- test -r "$STATE_DIR/setup-last-warning"
run runuser -u growcentral -- test -r "$APP_DIR/.env"
run runuser -u growcentral -- test -w "$APP_DIR/.env"
run runuser -u growcentral -- test -w "$APP_DIR/data"
run runuser -u growcentral -- test -w "$APP_DIR/app/main.py"
run runuser -u growcentral -- test -r /dev/video0
run runuser -u growcentral -- test -w /dev/video0
run stat /etc/polkit-1/rules.d/60-grow-central-network.rules
run runuser -u growcentral -- curl --fail --silent --show-error --max-time 5 http://127.0.0.1:8080/api/health

outcome=snapshot
if (( BOOT_WATCH == 1 )); then
section "Live first-boot transition recorder"
echo "Aufzeichnungsdauer: maximal ${WATCH_SECONDS} Sekunden."
if (( BOOT_WATCH == 1 )); then
  echo "Automatischer Boot-Modus aktiv. Setup kann jetzt im Browser durchgeführt werden."
else
  echo "JETZT den Setup-Dialog im Browser ausfüllen und auf Speichern klicken."
  echo "Dieses Terminal geöffnet lassen. Der Wechsel vom Setup-AP zur Haupt-GUI wird vollständig aufgezeichnet."
fi

TRANSITION_LOG=${WORK_DIR}/transition-timeline.log
NM_MONITOR_LOG=${WORK_DIR}/networkmanager-monitor.log
JOURNAL_FOLLOW_LOG=${WORK_DIR}/transition-journal.log
START_INVOCATION=$(systemctl show grow-central-apply-setup.service -p InvocationID --value 2>/dev/null || true)
START_ERROR_MTIME=$(stat -c %Y "$STATE_DIR/setup-last-error" 2>/dev/null || echo 0)
START_PENDING_MTIME=$(stat -c %Y "$STATE_DIR/setup-pending.json" 2>/dev/null || echo 0)

stdbuf -oL -eL nmcli monitor >"$NM_MONITOR_LOG" 2>&1 &
MONITOR_PIDS+=("$!")
journalctl -f -b --since now -o short-precise \
  -u grow-central-apply-setup.service \
  -u grow-central-apply-setup.path \
  -u grow-central-setup-ap.service \
  -u 135er-grow-central.service \
  -u NetworkManager.service \
  -u avahi-daemon.service >"$JOURNAL_FOLLOW_LOG" 2>&1 &
MONITOR_PIDS+=("$!")

attempt_seen=0
if journalctl -b -u grow-central-apply-setup.service --no-pager -q 2>/dev/null | grep -q .; then
  attempt_seen=1
fi
outcome=timeout
failed_since=0
started_epoch=$(date +%s)
deadline=$((started_epoch + WATCH_SECONDS))
while (( $(date +%s) < deadline )); do
  now=$(date +%s)
  timestamp=$(date --iso-8601=seconds)
  invocation=$(systemctl show grow-central-apply-setup.service -p InvocationID --value 2>/dev/null || true)
  apply_active=$(systemctl is-active grow-central-apply-setup.service 2>/dev/null || true)
  apply_result=$(systemctl show grow-central-apply-setup.service -p Result --value 2>/dev/null || true)
  app_active=$(systemctl is-active 135er-grow-central.service 2>/dev/null || true)
  avahi_active=$(systemctl is-active avahi-daemon.service 2>/dev/null || true)
  active_connections=$(nmcli -t -f NAME,DEVICE connection show --active 2>/dev/null | tr '\n' ',' || true)
  wlan_ipv4=$(ip -4 -o address show dev wlan0 scope global 2>/dev/null | awk '{print $4}' | tr '\n' ',' || true)
  default_route=$(ip -4 route show default 2>/dev/null | tr '\n' ',' || true)
  pending_mtime=$(stat -c %Y "$STATE_DIR/setup-pending.json" 2>/dev/null || echo 0)
  error_mtime=$(stat -c %Y "$STATE_DIR/setup-last-error" 2>/dev/null || echo 0)
  marker=$([[ -e "$STATE_DIR/.provisioned" ]] && echo yes || echo no)
  health_code=$(curl --silent --output /dev/null --write-out '%{http_code}' --max-time 2 http://127.0.0.1:8080/api/health 2>/dev/null || echo 000)
  setup_code=$(curl --silent --output /dev/null --write-out '%{http_code}' --max-time 2 http://127.0.0.1:8080/api/setup/status 2>/dev/null || echo 000)
  root_result=$(curl --silent --output /tmp/gc-debug-root-body --write-out '%{http_code}:%{redirect_url}' --max-time 2 http://127.0.0.1:8080/ 2>/dev/null || echo 000:)
  root_kind=unknown
  if grep -qi 'Grow Central Setup' /tmp/gc-debug-root-body 2>/dev/null; then
    root_kind=setup
  elif grep -qi '135er-Grow Central' /tmp/gc-debug-root-body 2>/dev/null; then
    root_kind=main-gui
  elif grep -qi 'anmelden\|login' /tmp/gc-debug-root-body 2>/dev/null; then
    root_kind=login
  fi

  printf '%s attempt=%s apply=%s result=%s app=%s avahi=%s marker=%s health_http=%s setup_http=%s root=%q root_kind=%s active=%q wlan4=%q default=%q\n' \
    "$timestamp" "$attempt_seen" "$apply_active" "$apply_result" "$app_active" "$avahi_active" \
    "$marker" "$health_code" "$setup_code" "$root_result" "$root_kind" "$active_connections" "$wlan_ipv4" "$default_route" \
    | tee -a "$TRANSITION_LOG"

  if [[ -n "$invocation" && "$invocation" != "$START_INVOCATION" ]] \
    || (( pending_mtime > START_PENDING_MTIME )) \
    || [[ "$apply_active" == activating || "$apply_active" == active ]]; then
    attempt_seen=1
  fi

  if (( attempt_seen == 1 )) \
    && [[ "$marker" == yes && "$app_active" == active && "$avahi_active" == active ]] \
    && { [[ "$active_connections" == *grow-central-uplink:wlan0* ]] || [[ "$active_connections" == *:eth0* ]]; } \
    && [[ "$health_code" == 200 ]]; then
    outcome=success
    echo "Übergang erfolgreich erkannt; zeichne 10 Sekunden Nachlauf auf." | tee -a "$TRANSITION_LOG"
    sleep 10
    break
  fi

  if (( attempt_seen == 1 )) && [[ "$apply_active" == failed ]] && (( error_mtime > START_ERROR_MTIME )); then
    if (( failed_since == 0 )); then
      failed_since=$now
      echo "Neuer Setup-Fehler erkannt; zeichne 20 Sekunden Nachlauf auf." | tee -a "$TRANSITION_LOG"
    elif (( now - failed_since >= 20 )); then
      outcome=failed
      break
    fi
  else
    failed_since=0
  fi
  sleep 2
done
stop_monitors
echo "Transition outcome: $outcome" | tee -a "$TRANSITION_LOG"

section "Post-transition state"
for unit in grow-central-apply-setup.service grow-central-setup-ap.service 135er-grow-central.service NetworkManager.service avahi-daemon.service; do
  run systemctl status "$unit" --no-pager -l
done
run nmcli -f DEVICE,TYPE,STATE,CONNECTION device status
run nmcli -f NAME,UUID,TYPE,DEVICE,AUTOCONNECT,AUTOCONNECT-PRIORITY connection show
run ip -4 address show
run ip route show
run resolvectl status
run getent ahostsv4 135er-grow-central.local
run curl --fail --silent --show-error --max-time 5 http://127.0.0.1:8080/api/health
run curl --silent --show-error --max-time 5 --dump-header - http://127.0.0.1:8080/
if [[ -r "$STATE_DIR/setup-last-error" ]]; then
  run sed -n 1,20p "$STATE_DIR/setup-last-error"
fi
fi

section "Summary"
{
  echo "Archive created: $(date --iso-8601=seconds)"
  echo "Hostname: $(hostname)"
  echo "Kernel: $(uname -r)"
  echo "Active connection: $(nmcli -t -f NAME,DEVICE connection show --active 2>/dev/null | tr '\n' ' ')"
  echo "IPv4: $(ip -4 -o address show scope global 2>/dev/null | awk '{print $2 "=" $4}' | tr '\n' ' ')"
  echo "Grow Central: $(systemctl is-active 135er-grow-central.service 2>/dev/null)"
  echo "Apply setup: $(systemctl is-active grow-central-apply-setup.service 2>/dev/null)"
  echo "Avahi: $(systemctl is-active avahi-daemon.service 2>/dev/null)"
  echo "Setup error present: $([[ -e $STATE_DIR/setup-last-error ]] && echo yes || echo no)"
  echo "Provisioned marker present: $([[ -e $STATE_DIR/.provisioned ]] && echo yes || echo no)"
  echo "Recorded transition outcome: ${outcome:-not-run}"
} | tee "$SUMMARY_FILE"

section "Create archive"
create_archive
if (( BOOT_WATCH == 1 )); then
  touch "$DEBUG_DONE"
  chown root:growcentral "$DEBUG_DONE" 2>/dev/null || true
  chmod 640 "$DEBUG_DONE"
fi
echo
echo "FERTIG: $ARCHIVE"
echo "Bitte nur diese .tar.gz-Datei zur Auswertung bereitstellen."
echo "Hinweis: SSID, IP- und MAC-Adressen sind für die Netzwerkanalyse enthalten; Passwörter und Secret-Werte nicht."
