#!/usr/bin/env python3
"""Apply validated first-boot configuration without logging secrets."""
from __future__ import annotations

import base64
import grp
import hashlib
import json
import os
import re
import secrets
import subprocess
import tempfile
import time
from pathlib import Path

STATE_DIR = Path("/var/lib/135er-grow-central")
PENDING_FILE = STATE_DIR / "setup-pending.json"
MARKER = STATE_DIR / ".provisioned"
ERROR_FILE = STATE_DIR / "setup-last-error"
WARNING_FILE = STATE_DIR / "setup-last-warning"
APP_ENV = Path("/opt/135er-grow-central/.env")
FIXED_HOSTNAME = "135er-grow-central"
AP_CONNECTION = "grow-central-setup-ap"
TARGET_CONNECTION = "grow-central-uplink"
GUI_USER_RE = re.compile(r"^[A-Za-z0-9._-]{3,32}$")
TIMEZONES = {"Europe/Berlin", "UTC", "Europe/Vienna", "Europe/Zurich"}
HOSTS_FILE = Path("/etc/hosts")
PBKDF2_ITERATIONS = 240_000


def run(*arguments: str, check: bool = True, input_text: str | None = None) -> subprocess.CompletedProcess[str]:
    return subprocess.run(arguments, check=check, text=True, input=input_text, capture_output=True)


def update_hosts(hostname: str, hosts_file: Path = HOSTS_FILE) -> None:
    lines = hosts_file.read_text(encoding="utf-8").splitlines()
    replacement = f"127.0.1.1\t{hostname}"
    updated = False
    for index, line in enumerate(lines):
        if line.split("#", 1)[0].split()[:1] == ["127.0.1.1"]:
            lines[index] = replacement
            updated = True
            break
    if not updated:
        lines.append(replacement)
    temporary = hosts_file.with_name(f".{hosts_file.name}.grow-central.tmp")
    temporary.write_text("\n".join(lines) + "\n", encoding="utf-8")
    os.chmod(temporary, 0o644)
    os.replace(temporary, hosts_file)


def validate(config: dict[str, str]) -> None:
    if config.get("mode") not in {"wifi", "ethernet"}:
        raise ValueError("invalid network mode")
    if config.get("hostname") != FIXED_HOSTNAME:
        raise ValueError("invalid hostname")
    if config.get("timezone") not in TIMEZONES:
        raise ValueError("invalid timezone")
    if len(config.get("new_password", "")) < 12:
        raise ValueError("invalid system password")
    if config["mode"] == "wifi":
        ssid = config.get("ssid", "")
        wifi_password = config.get("wifi_password", "")
        if not 1 <= len(ssid.encode("utf-8")) <= 32:
            raise ValueError("invalid ssid")
        if wifi_password and not 8 <= len(wifi_password) <= 63:
            raise ValueError("invalid wifi password")
    if not GUI_USER_RE.fullmatch(config.get("gui_username", "")):
        raise ValueError("invalid GUI username")
    if len(config.get("gui_password", "")) < 12:
        raise ValueError("invalid GUI password")
    fritz_enabled = config.get("fritz_enabled") == "1"
    if fritz_enabled and not all((config.get("fritz_host", "").strip(), config.get("fritz_username", "").strip(), config.get("fritz_password", ""))):
        raise ValueError("incomplete FRITZ credentials")


def _quote_env(value: str) -> str:
    return '"' + value.replace("\\", "\\\\").replace('"', '\\"').replace("\n", "") + '"'


def _gui_hash(password: str) -> str:
    salt = secrets.token_bytes(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, PBKDF2_ITERATIONS)
    salt_text = base64.urlsafe_b64encode(salt).decode("ascii").rstrip("=")
    digest_text = base64.urlsafe_b64encode(digest).decode("ascii").rstrip("=")
    return f"pbkdf2_sha256${PBKDF2_ITERATIONS}${salt_text}${digest_text}"


def persist_runtime_settings(config: dict[str, str]) -> None:
    existing = APP_ENV.read_text(encoding="utf-8").splitlines() if APP_ENV.exists() else []
    values = {
        "GC_GUI_USERNAME": config["gui_username"].strip(),
        "GC_GUI_PASSWORD_HASH": _gui_hash(config["gui_password"]),
        "GC_SMARTHOME_ENABLED": "true",
        "GC_FRITZ_HOST": config.get("fritz_host", "").strip() if config.get("fritz_enabled") == "1" else "",
        "GC_FRITZ_USERNAME": config.get("fritz_username", "").strip() if config.get("fritz_enabled") == "1" else "",
        "GC_FRITZ_PASSWORD": config.get("fritz_password", "") if config.get("fritz_enabled") == "1" else "",
    }
    keys = set(values)
    filtered = [line for line in existing if line.split("=", 1)[0] not in keys]
    for key, value in values.items():
        if value or key == "GC_SMARTHOME_ENABLED":
            filtered.append(f"{key}={_quote_env(value)}")
    temporary = APP_ENV.with_suffix(".env.tmp")
    descriptor = os.open(temporary, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o640)
    with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
        handle.write("\n".join(filtered).rstrip() + "\n")
        handle.flush()
        os.fsync(handle.fileno())
    growcentral_gid = grp.getgrnam("growcentral").gr_gid
    os.chown(temporary, 0, growcentral_gid)
    os.replace(temporary, APP_ENV)


def restore_runtime_settings(previous: bytes | None) -> None:
    if previous is None:
        APP_ENV.unlink(missing_ok=True)
        return
    temporary = APP_ENV.with_suffix(".env.rollback")
    descriptor = os.open(temporary, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o640)
    with os.fdopen(descriptor, "wb") as handle:
        handle.write(previous)
        handle.flush()
        os.fsync(handle.fileno())
    os.chown(temporary, 0, grp.getgrnam("growcentral").gr_gid)
    os.replace(temporary, APP_ENV)


def install_runtime_policy() -> None:
    """Switch the systemd service to the protected entry point and allow only NetworkManager actions needed by the GUI."""
    dropin_dir = Path("/etc/systemd/system/135er-grow-central.service.d")
    dropin_dir.mkdir(parents=True, exist_ok=True)
    dropin = dropin_dir / "20-protected-runtime.conf"
    dropin.write_text(
        "[Service]\n"
        "ExecStart=\n"
        "ExecStart=/opt/135er-grow-central/.venv/bin/uvicorn app.entrypoint:app --host 0.0.0.0 --port 8080\n"
        "SupplementaryGroups=systemd-journal video netdev\n",
        encoding="utf-8",
    )
    os.chmod(dropin, 0o644)

    polkit_dir = Path("/etc/polkit-1/rules.d")
    if polkit_dir.exists():
        rule = polkit_dir / "60-grow-central-network.rules"
        rule.write_text(
            "polkit.addRule(function(action, subject) {\n"
            "  var allowed = [\n"
            "    'org.freedesktop.NetworkManager.network-control',\n"
            "    'org.freedesktop.NetworkManager.settings.modify.system',\n"
            "    'org.freedesktop.NetworkManager.settings.modify.own'\n"
            "  ];\n"
            "  if (subject.user == 'growcentral' && allowed.indexOf(action.id) >= 0) {\n"
            "    return polkit.Result.YES;\n"
            "  }\n"
            "});\n",
            encoding="utf-8",
        )
        os.chmod(rule, 0o644)
    run("usermod", "-aG", "video,netdev", "growcentral", check=False)
    run("systemctl", "daemon-reload")


def restore_access_point(message: str) -> None:
    MARKER.unlink(missing_ok=True)
    ERROR_FILE.write_text(message[:500] + "\n", encoding="utf-8")
    os.chmod(ERROR_FILE, 0o640)
    os.chown(ERROR_FILE, 0, grp.getgrnam("growcentral").gr_gid)
    run("nmcli", "connection", "down", TARGET_CONNECTION, check=False)
    run("nmcli", "connection", "up", AP_CONNECTION, check=False)


def write_warning(message: str) -> None:
    WARNING_FILE.write_text(message[:500] + "\n", encoding="utf-8")
    os.chmod(WARNING_FILE, 0o640)
    os.chown(WARNING_FILE, 0, grp.getgrnam("growcentral").gr_gid)


def mark_provisioned() -> None:
    STATE_DIR.mkdir(mode=0o750, parents=True, exist_ok=True)
    temporary = MARKER.with_suffix(".tmp")
    descriptor = os.open(temporary, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o640)
    with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
        handle.write(f"provisioned_at={time.time_ns()}\n")
        handle.flush()
        os.fsync(handle.fileno())
    os.replace(temporary, MARKER)


def configure_wifi(config: dict[str, str]) -> None:
    run("nmcli", "connection", "delete", TARGET_CONNECTION, check=False)
    run("nmcli", "connection", "add", "type", "wifi", "ifname", "wlan0", "con-name", TARGET_CONNECTION, "ssid", config["ssid"])
    run("nmcli", "connection", "modify", TARGET_CONNECTION, "connection.autoconnect", "yes", "connection.autoconnect-priority", "50", "ipv4.method", "auto", "ipv6.method", "auto")
    if config.get("wifi_password"):
        run("nmcli", "connection", "modify", TARGET_CONNECTION, "wifi-sec.key-mgmt", "wpa-psk")
    run("nmcli", "connection", "down", AP_CONNECTION, check=False)
    password_file = None
    arguments = ["nmcli", "--wait", "35", "connection", "up", TARGET_CONNECTION]
    if config.get("wifi_password"):
        descriptor, password_file = tempfile.mkstemp(prefix="grow-central-wifi-", dir="/run", text=True)
        os.fchmod(descriptor, 0o600)
        with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
            handle.write(f"802-11-wireless-security.psk:{config['wifi_password']}\n")
        arguments.extend(["passwd-file", password_file])
    try:
        result = run(*arguments, check=False)
    finally:
        if password_file:
            Path(password_file).unlink(missing_ok=True)
    if result.returncode != 0:
        run("nmcli", "connection", "delete", TARGET_CONNECTION, check=False)
        raise RuntimeError("Das gewählte WLAN konnte nicht verbunden werden.")


def active_ipv4(device: str) -> str:
    result = run("ip", "-4", "-o", "address", "show", "dev", device, "scope", "global", check=False)
    if result.returncode != 0 or not result.stdout.strip():
        raise RuntimeError(f"{device} hat keine nutzbare IPv4-Adresse erhalten.")
    return result.stdout.split()[3].split("/", 1)[0]


def verify_network(device: str) -> str:
    address = active_ipv4(device)
    route = run("ip", "route", "show", "default", "dev", device, check=False)
    if route.returncode != 0 or not route.stdout.strip():
        raise RuntimeError(f"Für {device} wurde kein Standard-Gateway gefunden.")
    dns = run("getent", "ahostsv4", "www.debian.org", check=False)
    if dns.returncode != 0 or not dns.stdout.strip():
        raise RuntimeError("Die DNS-Auflösung über das Heimnetz ist fehlgeschlagen.")
    internet = run(
        "curl", "--ipv4", "--interface", device, "--fail", "--silent", "--show-error", "--location",
        "--max-time", "15", "--output", "/dev/null", "https://www.debian.org/", check=False,
    )
    if internet.returncode != 0:
        write_warning(
            "Heimnetz und DNS funktionieren, aber der externe Internet-Test konnte nicht bestätigt werden. "
            "Das Setup wurde trotzdem abgeschlossen."
        )
    else:
        WARNING_FILE.unlink(missing_ok=True)
    return address


def verify_runtime(address: str) -> None:
    deadline = time.monotonic() + 60
    pending = {"127.0.0.1", address}
    while time.monotonic() < deadline:
        active = run("systemctl", "is-active", "135er-grow-central.service", check=False)
        if active.returncode == 0:
            for target in tuple(pending):
                health = run("curl", "--fail", "--silent", "--max-time", "3", f"http://{target}:8080/api/health", check=False)
                if health.returncode == 0:
                    pending.discard(target)
            if not pending:
                break
        time.sleep(2)
    if pending:
        targets = ", ".join(f"{target}:8080" for target in sorted(pending))
        raise RuntimeError(f"Die Grow-Central-Oberfläche wurde innerhalb von 60 Sekunden nicht über {targets} erreichbar.")
    avahi = run("systemctl", "is-active", "avahi-daemon.service", check=False)
    if avahi.returncode != 0:
        raise RuntimeError("Die Erreichbarkeit über den lokalen Hostnamen konnte nicht aktiviert werden.")


def main() -> int:
    if not PENDING_FILE.exists():
        return 0
    config = json.loads(PENDING_FILE.read_text(encoding="utf-8"))
    PENDING_FILE.unlink(missing_ok=True)
    ERROR_FILE.unlink(missing_ok=True)
    previous_env = APP_ENV.read_bytes() if APP_ENV.exists() else None
    runtime_settings_changed = False
    system_credential = ""
    try:
        validate(config)
        system_credential = config["new_password"]
        if config["mode"] == "wifi":
            configure_wifi(config)
        network_device = "wlan0" if config["mode"] == "wifi" else "eth0"
        network_address = verify_network(network_device)
        run("hostnamectl", "set-hostname", config["hostname"])
        update_hosts(config["hostname"])
        run("systemctl", "restart", "avahi-daemon.service", check=False)
        run("timedatectl", "set-timezone", config["timezone"])
        persist_runtime_settings(config)
        runtime_settings_changed = True
        install_runtime_policy()
        network_mode = config["mode"]
        config.clear()
        ERROR_FILE.unlink(missing_ok=True)
        keep_access_point = network_mode == "ethernet"
        run("nmcli", "connection", "modify", AP_CONNECTION, "connection.autoconnect", "yes" if keep_access_point else "no", check=False)
        if not keep_access_point:
            run("nmcli", "connection", "down", AP_CONNECTION, check=False)
        run("ufw", "--force", "delete", "allow", "in", "on", "wlan0", "to", "any", "port", "80", "proto", "tcp", check=False)
        run("ufw", "--force", "delete", "allow", "in", "on", "wlan0", "to", "any", "port", "443", "proto", "tcp", check=False)
        if not keep_access_point:
            run("ufw", "--force", "delete", "allow", "in", "on", "wlan0", "to", "any", "port", "67", "proto", "udp", check=False)
            run("ufw", "--force", "delete", "allow", "in", "on", "wlan0", "to", "any", "port", "53", "proto", "udp", check=False)
            run("ufw", "--force", "delete", "allow", "in", "on", "wlan0", "to", "any", "port", "53", "proto", "tcp", check=False)
        run("systemctl", "reset-failed", "135er-grow-central.service", check=False)
        run("systemctl", "restart", "135er-grow-central.service")
        verify_runtime(network_address)
        run("chpasswd", input_text=f"GrowCentral:{system_credential}\n")
        system_credential = ""
        mark_provisioned()
        return 0
    except Exception as error:
        config.clear()
        system_credential = ""
        if runtime_settings_changed:
            restore_runtime_settings(previous_env)
            run("systemctl", "restart", "135er-grow-central.service", check=False)
        restore_access_point(str(error))
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
