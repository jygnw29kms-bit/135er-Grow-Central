"""Mars Legacy BLE observation parsers, read-only and identifier-redacted.

The MZF002 field map was observed in iPhone HCI captures on 2026-11-12.
This module never opens BLE connections or writes to characteristics. The
CFM/Pa are explicitly labelled SHOW/estimated, never sensor readings.
"""
from __future__ import annotations

import math
import re
from typing import Any

_NUM = re.compile(r"^-?\d+(?:[.,]\d+)?$")


def _number(value: str) -> float | None:
    if not _NUM.fullmatch(value):
        return None
    x = float(value.replace(",", "."))
    return x if math.isfinite(x) else None


def mzf002_display_estimates(power_on: bool, setpoint_percent: int) -> dict[str, Any]:
    """Optional display-only Mars Legacy-style curve fitted to 25/50/59% snapshots.

    Not actual measured airflow or static pressure. Never feed control loops.
    """
    if not power_on or setpoint_percent <= 0:
        cfm = pa = 0.0
    else:
        cfm = max(0.0, round(19.0 + 3.8 * setpoint_percent, 1))
        pa = max(0.0, round(5.6 * setpoint_percent - 90.0, 1))
    return {
        "airflow_cfm": cfm,
        "pressure_pa": pa,
        "airflow_pressure_source": "estimated_from_setpoint_show_only",
        "airflow_pressure_measured": False,
    }


def mzf002_telemetry(data: bytes) -> dict[str, Any] | None:
    """Parse one complete MZF002 notify payload, without retaining identifiers.

    No assertion about other device families, message types, or disconnections.
    """
    if not data or len(data) > 512:
        return None
    try:
        fields = data.decode("ascii").strip("\r\n").split("|")
    except UnicodeDecodeError:
        return None
    if len(fields) != 23 or fields[3] != "MZF002":
        return None
    temp = _number(fields[19])
    humidity = _number(fields[20])
    if temp is None or humidity is None or not fields[21].isdigit():
        return None
    rpm = int(fields[21])
    if not (-40 <= temp <= 85 and 0 <= humidity <= 100 and 0 <= rpm <= 10000):
        return None
    if fields[12] not in ("0", "1") or not fields[13].isdigit():
        return None
    setpoint = int(fields[13])
    if not 0 <= setpoint <= 100:
        return None
    return {
        "device_family": "MZF002",
        "power_on": fields[12] == "1",
        "setpoint_percent": setpoint,
        "temperature_c": temp,
        "humidity_rh": humidity,
        "rpm": rpm,
        **mzf002_display_estimates(fields[12] == "1", setpoint),
        "decoded_fields": [12, 13, 19, 20, 21],
        "interpretation": "observed_from_mars_legacy_hci",
        "read_only": True,
        "identity_verified": False,
        "control_verified": False,
    }


def fc3000_telemetry(data: bytes) -> dict[str, Any] | None:
    """Decode only the 19-field Mars Legacy FC3000 status observed on real iPhone HCI.

    Original app action windows independently confirmed that index 12 is power
    and 13 is brightness (24/26/50/75/76/25%). This is a read-only status
    parser; it never authenticates to or commands the lamp.
    """
    if not data or len(data) > 512:
        return None
    try:
        fields = data.decode("ascii").strip(chr(13) + chr(10)).split("|")
    except UnicodeDecodeError:
        return None
    if len(fields) != 19 or fields[3] != "MARS":
        return None
    if fields[12] not in ("0", "1") or not fields[13].isdigit():
        return None
    brightness = int(fields[13])
    if brightness < 0 or brightness > 100:
        return None
    version = fields[4]
    if not re.fullmatch(r"[0-9]{1,3}(?:[.][0-9]{1,3}){1,2}", version):
        return None
    return {
        "device_family": "MARS",
        "power_on": fields[12] == "1",
        "brightness_percent": brightness,
        "firmware_version": version,
        "decoded_fields": [3, 4, 12, 13],
        "interpretation": "correlated_with_real_mars_legacy_fc3000_actions",
        "read_only": True,
        "identity_verified": False,
        "control_verified": False,
    }
