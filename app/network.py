"""Local network management API for the Raspberry Pi appliance.

Read operations are available to the local GUI. Joining a WLAN is protected by
the local write token and uses NetworkManager through nmcli without shell
interpolation. Passwords are never returned or logged.
"""
from __future__ import annotations

import asyncio
import json
import subprocess
from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from app.audit import append_audit
from app.hardware import wifi_interface
from app.security import require_write_auth

router = APIRouter(prefix="/api/v1/network", tags=["network"])


class WifiJoinRequest(BaseModel):
    ssid: str = Field(min_length=1, max_length=32)
    password: str = Field(default="", max_length=63)


def _run(arguments: list[str], timeout: int = 12) -> subprocess.CompletedProcess[str]:
    return subprocess.run(arguments, capture_output=True, text=True, timeout=timeout, check=False)


def _nmcli_fields(line: str) -> list[str]:
    result: list[str] = []
    current: list[str] = []
    escaped = False
    for character in line:
        if escaped:
            current.append(character)
            escaped = False
        elif character == "\\":
            escaped = True
        elif character == ":":
            result.append("".join(current))
            current = []
        else:
            current.append(character)
    result.append("".join(current))
    return result


def _status_sync() -> dict[str, Any]:
    try:
        result = _run(["nmcli", "-t", "-e", "yes", "-f", "DEVICE,TYPE,STATE,CONNECTION", "device", "status"])
    except (OSError, subprocess.TimeoutExpired) as exc:
        return {"ok": False, "error": type(exc).__name__, "interfaces": []}
    rows = []
    if result.returncode == 0:
        for line in result.stdout.splitlines():
            fields = _nmcli_fields(line)
            if len(fields) >= 4:
                rows.append({"device": fields[0], "type": fields[1], "state": fields[2], "connection": fields[3]})
    connected = [row for row in rows if row["state"] in {"connected", "verbunden"}]
    return {"ok": result.returncode == 0, "interfaces": rows, "connected": connected}


def _scan_sync() -> dict[str, Any]:
    wlan = wifi_interface()
    if not wlan:
        return {"ok": False, "error": "wifi-unavailable", "message": "Keine WLAN-Schnittstelle erkannt.", "networks": []}
    try:
        _run(["nmcli", "device", "wifi", "rescan", "ifname", wlan], timeout=20)
        result = _run(["nmcli", "-t", "-e", "yes", "-f", "SSID,SIGNAL,SECURITY,IN-USE", "device", "wifi", "list", "ifname", wlan, "--rescan", "auto"], timeout=20)
    except subprocess.TimeoutExpired:
        return {"ok": False, "error": "timeout", "message": "WLAN-Suche hat das Zeitlimit überschritten.", "networks": []}
    except OSError:
        return {"ok": False, "error": "nmcli-unavailable", "message": "NetworkManager/nmcli ist nicht verfügbar.", "networks": []}
    if result.returncode != 0:
        detail = (result.stderr or "").strip()[:180]
        return {"ok": False, "error": "scan-failed", "message": detail or "WLAN-Suche fehlgeschlagen.", "networks": []}
    found: dict[str, dict[str, Any]] = {}
    for line in result.stdout.splitlines():
        fields = _nmcli_fields(line)
        if len(fields) < 4:
            continue
        ssid, signal, security, in_use = (item.strip() for item in fields[:4])
        if not ssid:
            continue
        row = {"ssid": ssid, "signal": int(signal) if signal.isdigit() else 0, "security": security or "OPEN", "connected": in_use == "*"}
        previous = found.get(ssid)
        if previous is None or row["signal"] > previous["signal"]:
            found[ssid] = row
    rows = sorted(found.values(), key=lambda item: (not item["connected"], -item["signal"], item["ssid"].lower()))
    return {"ok": True, "count": len(rows), "networks": rows}


def _join_sync(request: WifiJoinRequest) -> dict[str, Any]:
    # nmcli accepts secrets through stdin with --ask; this avoids putting the
    # WLAN password in process arguments. The SSID is passed as a single argv.
    wlan = wifi_interface()
    if not wlan:
        raise HTTPException(503, "Keine WLAN-Schnittstelle erkannt")
    cmd = ["nmcli", "--wait", "35", "device", "wifi", "connect", request.ssid, "ifname", wlan]
    input_text = ""
    if request.password:
        cmd.append("--ask")
        input_text = request.password + "\n"
    try:
        result = subprocess.run(cmd, input=input_text, capture_output=True, text=True, timeout=45, check=False)
    except subprocess.TimeoutExpired as exc:
        raise HTTPException(504, "WLAN-Verbindung hat das Zeitlimit überschritten") from exc
    except OSError as exc:
        raise HTTPException(503, "NetworkManager/nmcli ist nicht verfügbar") from exc
    if result.returncode != 0:
        detail = (result.stderr or result.stdout or "").strip()[:180]
        raise HTTPException(502, detail or "WLAN-Verbindung fehlgeschlagen")
    return {"ok": True, "ssid": request.ssid}


@router.get("/status")
async def network_status():
    return await asyncio.to_thread(_status_sync)


@router.get("/wifi")
async def wifi_scan():
    return await asyncio.to_thread(_scan_sync)


@router.post("/wifi/join", dependencies=[Depends(require_write_auth)])
async def wifi_join(request: WifiJoinRequest):
    result = await asyncio.to_thread(_join_sync, request)
    append_audit("network.wifi.join", ssid=request.ssid, ok=True)
    return result
