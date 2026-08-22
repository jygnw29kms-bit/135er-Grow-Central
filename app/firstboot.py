"""First-boot setup served by the always-on main application."""
from __future__ import annotations

import json
import os
import re
import subprocess
from pathlib import Path

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, SecretStr
from app.hardware import ethernet_interface, wifi_interface

STATE_DIR = Path("/var/lib/135er-grow-central")
PENDING_FILE = STATE_DIR / "setup-pending.json"
MARKER = STATE_DIR / ".provisioned"
FIXED_HOSTNAME = "135er-grow-central"
GUI_USER_RE = re.compile(r"^[A-Za-z0-9._-]{3,32}$")
TIMEZONES = {"Europe/Berlin", "UTC", "Europe/Vienna", "Europe/Zurich"}

router = APIRouter(prefix="/api/setup", tags=["firstboot"])


class SetupBody(BaseModel):
    mode: str
    timezone: str
    ssid: str = ""
    wifi_password: SecretStr = SecretStr("")
    new_password: SecretStr
    gui_username: str
    gui_password: SecretStr
    fritz_enabled: bool = False
    fritz_host: str = ""
    fritz_username: str = ""
    fritz_password: SecretStr = SecretStr("")


def setup_active() -> bool:
    return not MARKER.is_file()


def _command(*arguments: str, timeout: int = 15) -> subprocess.CompletedProcess[str]:
    return subprocess.run(arguments, capture_output=True, text=True, timeout=timeout, check=False)


def _device_state(device: str) -> dict[str, object]:
    result = _command("nmcli", "-t", "-f", "GENERAL.STATE,IP4.ADDRESS", "device", "show", device)
    connected = result.returncode == 0 and any(
        line.startswith("GENERAL.STATE:") and "(connected)" in line for line in result.stdout.splitlines()
    )
    addresses = [line.split(":", 1)[1] for line in result.stdout.splitlines() if line.startswith("IP4.ADDRESS")]
    return {"connected": connected, "addresses": addresses}


@router.get("/status")
async def status():
    error = ""
    warning = ""
    if not PENDING_FILE.exists() and (STATE_DIR / "setup-last-error").is_file():
        try:
            error = (STATE_DIR / "setup-last-error").read_text(encoding="utf-8").strip()[:500]
        except OSError:
            error = "Die letzte Setup-Fehlermeldung konnte wegen falscher Dateirechte nicht gelesen werden."
    warning_file = STATE_DIR / "setup-last-warning"
    if warning_file.is_file():
        try:
            warning = warning_file.read_text(encoding="utf-8").strip()[:500]
        except OSError:
            warning = "Eine Setup-Warnung konnte nicht gelesen werden."
    return {"setup_required": setup_active(), "pending": PENDING_FILE.exists(), "error": error, "warning": warning}


@router.get("/network-status")
async def network_status():
    if not setup_active():
        raise HTTPException(404, "Setup abgeschlossen")
    lan = ethernet_interface()
    ethernet = _device_state(lan) if lan else {"connected": False, "addresses": []}
    ethernet["interface"] = lan
    connectivity = _command("nmcli", "networking", "connectivity", "check").stdout.strip().lower()
    ethernet["internet"] = ethernet["connected"] and connectivity == "full"
    return {"ethernet": ethernet, "connectivity": connectivity or "unknown"}


@router.get("/networks")
async def networks():
    if not setup_active():
        raise HTTPException(404, "Setup abgeschlossen")
    wlan = wifi_interface()
    if not wlan:
        raise HTTPException(503, "Keine von NetworkManager verwaltete WLAN-Schnittstelle erkannt")
    result = subprocess.run(
        ["nmcli", "-t", "-e", "yes", "-f", "SSID,SIGNAL,SECURITY", "device", "wifi", "list", "ifname", wlan, "--rescan", "auto"],
        capture_output=True, text=True, timeout=25, check=False,
    )
    if result.returncode != 0:
        raise HTTPException(503, (result.stderr or "WLAN-Suche fehlgeschlagen").strip()[:180])
    rows = []
    for line in result.stdout.splitlines():
        fields = re.split(r"(?<!\\):", line)
        if len(fields) == 3 and fields[0] and not fields[0].startswith("135er-GrowCentral-Setup-"):
            rows.append({"ssid": fields[0].replace(r"\:", ":"), "signal": fields[1], "security": fields[2]})
    active = _command("nmcli", "-t", "-f", "NAME,DEVICE", "connection", "show", "--active")
    setup_ap_active = f"grow-central-setup-ap:{wlan}" in active.stdout.splitlines()
    return {
        "networks": rows,
        "setup_ap_active": setup_ap_active,
        "wifi_interface": wlan,
        "manual_ssid_required": setup_ap_active and not rows,
        "message": (
            "Der Raspberry Pi 3B kann während des aktiven Setup-APs keine anderen WLANs zuverlässig anzeigen. "
            "Bitte die SSID manuell eintragen."
            if setup_ap_active and not rows else ""
        ),
    }


@router.post("/restart")
async def restart_setup():
    if PENDING_FILE.exists():
        raise HTTPException(409, "Setup wird bereits geprüft")
    MARKER.unlink(missing_ok=True)
    (STATE_DIR / "setup-last-error").unlink(missing_ok=True)
    (STATE_DIR / "setup-last-warning").unlink(missing_ok=True)
    return {"ok": True, "setup_required": True}


@router.post("")
async def apply(body: SetupBody):
    if not setup_active():
        raise HTTPException(409, "Setup bereits abgeschlossen")
    if PENDING_FILE.exists():
        raise HTTPException(409, "Setup wird bereits geprüft")
    if body.mode not in {"wifi", "ethernet"}:
        raise HTTPException(422, "Ungültiger Netzwerkmodus")
    if body.timezone not in TIMEZONES:
        raise HTTPException(422, "Zeitzone ungültig")
    if len(body.new_password.get_secret_value()) < 12 or not GUI_USER_RE.fullmatch(body.gui_username) or len(body.gui_password.get_secret_value()) < 12:
        raise HTTPException(422, "System- und GUI-Passwort müssen mindestens 12 Zeichen haben")
    if body.mode == "wifi" and (not 1 <= len(body.ssid.encode()) <= 32 or (body.wifi_password.get_secret_value() and not 8 <= len(body.wifi_password.get_secret_value()) <= 63)):
        raise HTTPException(422, "WLAN-Daten ungültig")
    if body.fritz_enabled and not (body.fritz_host and body.fritz_username and body.fritz_password.get_secret_value()):
        raise HTTPException(422, "FRITZ!-Zugangsdaten unvollständig")
    config = {
        "mode": body.mode, "hostname": FIXED_HOSTNAME, "timezone": body.timezone,
        "ssid": body.ssid, "wifi_password": body.wifi_password.get_secret_value(),
        "new_password": body.new_password.get_secret_value(), "gui_username": body.gui_username,
        "gui_password": body.gui_password.get_secret_value(), "fritz_enabled": "1" if body.fritz_enabled else "0",
        "fritz_host": body.fritz_host, "fritz_username": body.fritz_username,
        "fritz_password": body.fritz_password.get_secret_value(),
    }
    STATE_DIR.mkdir(mode=0o750, parents=True, exist_ok=True)
    temporary = PENDING_FILE.with_suffix(".tmp")
    descriptor = os.open(temporary, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
        json.dump(config, handle)
        handle.flush()
        os.fsync(handle.fileno())
    os.replace(temporary, PENDING_FILE)
    return {"ok": True, "state": "validating"}
