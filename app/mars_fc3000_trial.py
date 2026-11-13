"""Strict, hardware-bound FC3000 experimental control encoding.

No connectivity or writes here. Hardware transaction requires fresh MARS 3.4
notification, explicit authenticated user action, exact model allowlist and
BLE acknowledgement. Never return or log the private five-digit control code.
"""
from __future__ import annotations
import re
from app.mars_legacy_telemetry import fc3000_telemetry

_DEVICE = re.compile(r"^FC[A-F0-9]{10}$")
_TOKEN = re.compile(r"^[0-9]{5}$")


def context_from_live_status(payload: bytes) -> tuple[str, dict] | None:
    status = fc3000_telemetry(payload)
    if status is None or status["firmware_version"] != "3.4":
        return None
    try:
        parts = payload.decode("ascii").strip(chr(13) + chr(10)).split("|")
    except UnicodeDecodeError:
        return None
    code = parts[5]
    if not _TOKEN.fullmatch(code):
        return None
    return code, status


def encode_command(*, code: str, device_id: str, action: str, value: int) -> bytes:
    if not _TOKEN.fullmatch(code) or not _DEVICE.fullmatch(device_id):
        raise ValueError("Invalid private FC3000 context")
    if isinstance(value, bool) or not isinstance(value, int):
        raise ValueError("Invalid control value")
    if action == "power":
        if value not in (0, 1):
            raise ValueError("Power must be 0/1")
        kind = 1
    elif action == "brightness":
        if value < 10 or value > 100:
            raise ValueError("Brightness must be 10..100")
        kind = 2
    else:
        raise ValueError("Unsupported operation")
    return f"{kind}|0|{code}|{device_id}|{value}".encode("ascii")
