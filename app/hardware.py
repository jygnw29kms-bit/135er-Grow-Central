"""Raspberry Pi identity and network-interface discovery without fixed names."""
from __future__ import annotations

import json
import re
import subprocess
from pathlib import Path
from typing import Any

MODEL_PATH = Path("/proc/device-tree/model")
STATE_DIR = Path("/var/lib/135er-grow-central")


def classify_model(model: str) -> dict[str, Any]:
    normalized = model.replace("\x00", "").strip()
    patterns = (
        (r"Raspberry Pi 3 Model B Plus", "pi3b+", "BCM2837B0", True, True),
        (r"Raspberry Pi 3 Model B", "pi3b", "BCM2837", True, True),
        (r"Raspberry Pi 400", "pi400", "BCM2711", True, True),
        (r"Raspberry Pi 4 Model B", "pi4b", "BCM2711", True, True),
        (r"Raspberry Pi 5 Model B", "pi5", "BCM2712", True, True),
        (r"Raspberry Pi Compute Module 5", "cm5", "BCM2712", False, False),
        (r"Raspberry Pi Compute Module 4", "cm4", "BCM2711", False, False),
        (r"Raspberry Pi Compute Module 3(?: Plus|\+)?", "cm3", "BCM2837", False, False),
    )
    for pattern, profile, soc, onboard_wifi, onboard_bluetooth in patterns:
        if re.search(pattern, normalized, re.IGNORECASE):
            return {"model": normalized, "profile": profile, "soc": soc,
                    "onboard_wifi": onboard_wifi, "onboard_bluetooth": onboard_bluetooth,
                    "supported": True}
    is_pi = normalized.lower().startswith("raspberry pi")
    return {"model": normalized or "unknown", "profile": "raspberrypi" if is_pi else "unknown",
            "soc": "unknown", "onboard_wifi": None, "onboard_bluetooth": None,
            "supported": is_pi}


def _nmcli_devices() -> list[tuple[str, str]]:
    try:
        result = subprocess.run(
            ["nmcli", "-t", "-e", "yes", "-f", "DEVICE,TYPE", "device", "status"],
            capture_output=True, text=True, timeout=5, check=False,
        )
    except (OSError, subprocess.TimeoutExpired):
        return []
    rows = []
    for line in result.stdout.splitlines() if result.returncode == 0 else []:
        fields = re.split(r"(?<!\\):", line, maxsplit=1)
        if len(fields) == 2:
            rows.append((fields[0].replace(r"\:", ":"), fields[1]))
    return rows


def find_interface(kind: str, preferred: str) -> str | None:
    devices = _nmcli_devices()
    candidates = [name for name, device_type in devices if device_type == kind]
    if preferred in candidates:
        return preferred
    return next(iter(candidates), None)


def wifi_interface() -> str | None:
    saved = STATE_DIR / "hardware-wlan-interface"
    if saved.is_file():
        value = saved.read_text(encoding="utf-8", errors="replace").strip()
        if value:
            return value
    return find_interface("wifi", "wlan0")


def ethernet_interface() -> str | None:
    return find_interface("ethernet", "eth0")


def hardware_identity(model_path: Path = MODEL_PATH) -> dict[str, Any]:
    try:
        model = model_path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        model = ""
    identity = classify_model(model)
    identity.update({"wifi_interface": wifi_interface(), "ethernet_interface": ethernet_interface()})
    return identity


def diagnostic_json() -> str:
    return json.dumps(hardware_identity(), ensure_ascii=False, sort_keys=True)
