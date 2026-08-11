#!/usr/bin/env python3
"""Apply a validated first-boot configuration without logging secrets."""

from __future__ import annotations

import json
import os
import re
import subprocess
import tempfile
import time
from pathlib import Path


STATE_DIR = Path("/var/lib/135er-grow-central")
PENDING_FILE = STATE_DIR / "setup-pending.json"
MARKER = STATE_DIR / ".provisioned"
ERROR_FILE = STATE_DIR / "setup-last-error"
AP_CONNECTION = "grow-central-setup-ap"
TARGET_CONNECTION = "grow-central-uplink"
HOSTNAME_RE = re.compile(r"(?=^.{1,63}$)^[a-zA-Z0-9](?:[a-zA-Z0-9-]*[a-zA-Z0-9])?$")
TIMEZONES = {"Europe/Berlin", "UTC", "Europe/Vienna", "Europe/Zurich"}
HOSTS_FILE = Path("/etc/hosts")


def run(*arguments: str, check: bool = True, input_text: str | None = None) -> subprocess.CompletedProcess[str]:
    return subprocess.run(arguments, check=check, text=True, input=input_text, capture_output=True)


def update_hosts(hostname: str, hosts_file: Path = HOSTS_FILE) -> None:
    """Keep the local hostname resolvable after hostnamectl changes it."""
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
    if not HOSTNAME_RE.fullmatch(config.get("hostname", "")):
        raise ValueError("invalid hostname")
    if config.get("timezone") not in TIMEZONES:
        raise ValueError("invalid timezone")
    if len(config.get("new_password", "")) < 12:
        raise ValueError("invalid user password")
    if config["mode"] == "wifi":
        ssid = config.get("ssid", "")
        wifi_password = config.get("wifi_password", "")
        if not 1 <= len(ssid.encode("utf-8")) <= 32:
            raise ValueError("invalid ssid")
        if wifi_password and not 8 <= len(wifi_password) <= 63:
            raise ValueError("invalid wifi password")


def restore_access_point(message: str) -> None:
    MARKER.unlink(missing_ok=True)
    ERROR_FILE.write_text(message[:500] + "\n", encoding="utf-8")
    os.chmod(ERROR_FILE, 0o640)
    run("nmcli", "connection", "down", TARGET_CONNECTION, check=False)
    run("nmcli", "connection", "up", AP_CONNECTION, check=False)
    run("systemctl", "restart", "grow-central-firstboot-portal.service", check=False)


def mark_provisioned() -> None:
    """Commit provisioning atomically before asking systemd to start the UI."""
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
    settings = [
        "nmcli", "connection", "modify", TARGET_CONNECTION,
        "connection.autoconnect", "yes", "connection.autoconnect-priority", "50",
        "ipv4.method", "auto", "ipv6.method", "auto",
    ]
    run(*settings)
    if config.get("wifi_password"):
        run("nmcli", "connection", "modify", TARGET_CONNECTION, "wifi-sec.key-mgmt", "wpa-psk")
    run("nmcli", "connection", "down", AP_CONNECTION, check=False)
    password_file = None
    arguments = ["nmcli", "--wait", "35"]
    if config.get("wifi_password"):
        descriptor, password_file = tempfile.mkstemp(prefix="grow-central-wifi-", dir="/run", text=True)
        os.fchmod(descriptor, 0o600)
        with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
            handle.write(f"802-11-wireless-security.psk:{config['wifi_password']}\n")
        arguments.extend(["--passwd-file", password_file])
    arguments.extend(["connection", "up", TARGET_CONNECTION])
    try:
        result = run(*arguments, check=False)
    finally:
        if password_file:
            Path(password_file).unlink(missing_ok=True)
    if result.returncode != 0:
        run("nmcli", "connection", "delete", TARGET_CONNECTION, check=False)
        raise RuntimeError("Das gewählte WLAN konnte nicht verbunden werden.")


def main() -> int:
    if not PENDING_FILE.exists():
        return 0
    config = json.loads(PENDING_FILE.read_text(encoding="utf-8"))
    PENDING_FILE.unlink(missing_ok=True)
    try:
        validate(config)
        if config["mode"] == "wifi":
            configure_wifi(config)
        run("hostnamectl", "set-hostname", config["hostname"])
        update_hosts(config["hostname"])
        run("timedatectl", "set-timezone", config["timezone"])
        run("chpasswd", input_text=f"GrowCentral:{config['new_password']}\n")
        network_mode = config["mode"]
        config.clear()
        ERROR_FILE.unlink(missing_ok=True)
        mark_provisioned()
        # A wired installation keeps the AP as a local rescue/direct network.
        # With a single Wi-Fi adapter, client mode and AP mode cannot be kept
        # reliably at the same time, so Wi-Fi installations switch to uplink.
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
        time.sleep(2)
        run("systemctl", "stop", "grow-central-firstboot-portal.service", check=False)
        run("systemctl", "reset-failed", "135er-grow-central.service", check=False)
        run("systemctl", "start", "135er-grow-central.service")
        return 0
    except Exception as error:  # setup must recover its own access path
        config.clear()
        restore_access_point(str(error))
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
