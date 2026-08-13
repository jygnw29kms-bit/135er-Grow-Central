"""First-boot setup served by the always-on main application."""
from __future__ import annotations

import json
import os
import re
import secrets
import subprocess
from pathlib import Path

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field, SecretStr

STATE_DIR = Path("/var/lib/135er-grow-central")
PENDING_FILE = STATE_DIR / "setup-pending.json"
SETUP_FILE = Path(__file__).resolve().parent.parent / "web" / "setup.html"
HOSTNAME_RE = re.compile(r"(?=^.{1,63}$)^[a-zA-Z0-9](?:[a-zA-Z0-9-]*[a-zA-Z0-9])?$")
GUI_USER_RE = re.compile(r"^[A-Za-z0-9._-]{3,32}$")
TIMEZONES = {"Europe/Berlin", "UTC", "Europe/Vienna", "Europe/Zurich"}

router = APIRouter(prefix="/api/setup", tags=["firstboot"])


class SetupBody(BaseModel):
    setup_username: str
    setup_password: SecretStr
    mode: str
    hostname: str
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
    return SETUP_FILE.is_file()


@router.get("/status")
async def status():
    return {"setup_required": setup_active(), "pending": PENDING_FILE.exists()}


@router.get("/networks")
async def networks():
    if not setup_active():
        raise HTTPException(404, "Setup abgeschlossen")
    result = subprocess.run(
        ["nmcli", "-t", "-e", "yes", "-f", "SSID,SIGNAL,SECURITY", "device", "wifi", "list", "ifname", "wlan0", "--rescan", "auto"],
        capture_output=True, text=True, timeout=25, check=False,
    )
    if result.returncode != 0:
        raise HTTPException(503, (result.stderr or "WLAN-Suche fehlgeschlagen").strip()[:180])
    rows = []
    for line in result.stdout.splitlines():
        fields = re.split(r"(?<!\\):", line)
        if len(fields) == 3 and fields[0]:
            rows.append({"ssid": fields[0].replace(r"\:", ":"), "signal": fields[1], "security": fields[2]})
    return {"networks": rows}


@router.post("")
async def apply(body: SetupBody):
    if not setup_active():
        raise HTTPException(409, "Setup bereits abgeschlossen")
    if PENDING_FILE.exists():
        raise HTTPException(409, "Setup wird bereits geprüft")
    if not secrets.compare_digest(body.setup_username, "GrowCentral") or not secrets.compare_digest(body.setup_password.get_secret_value(), "grow-central-test"):
        raise HTTPException(401, "Temporäre Zugangsdaten falsch")
    if body.mode not in {"wifi", "ethernet"}:
        raise HTTPException(422, "Ungültiger Netzwerkmodus")
    if not HOSTNAME_RE.fullmatch(body.hostname.lower()) or body.timezone not in TIMEZONES:
        raise HTTPException(422, "Hostname oder Zeitzone ungültig")
    if len(body.new_password.get_secret_value()) < 12 or not GUI_USER_RE.fullmatch(body.gui_username) or len(body.gui_password.get_secret_value()) < 12:
        raise HTTPException(422, "System- und GUI-Passwort müssen mindestens 12 Zeichen haben")
    if body.mode == "wifi" and (not 1 <= len(body.ssid.encode()) <= 32 or (body.wifi_password.get_secret_value() and not 8 <= len(body.wifi_password.get_secret_value()) <= 63)):
        raise HTTPException(422, "WLAN-Daten ungültig")
    if body.fritz_enabled and not (body.fritz_host and body.fritz_username and body.fritz_password.get_secret_value()):
        raise HTTPException(422, "FRITZ!-Zugangsdaten unvollständig")
    config = {
        "mode": body.mode, "hostname": body.hostname.lower(), "timezone": body.timezone,
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
