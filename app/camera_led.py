"""Firmware-/modellabhängige Kamera-LED-Unterstützung.

Die Erweiterung hängt sich bewusst in die vorhandene Kamera-API ein. Eine LED-
Funktion wird nur angeboten, wenn die konkrete Kamera den Control tatsächlich
meldet. USB-ID und bcdDevice werden als Geräte-/Firmware-Revision erfasst.
"""
from __future__ import annotations

import os
import re
import shutil
from pathlib import Path
from typing import Any

from app import camera

VIRTUAL_LED_CONTROL = "Kamera_LED"
_NATIVE_LED_NAMES = {"led1_mode", "led_mode", "camera_led_mode"}

_ORIGINAL_DEVICE_INFO = camera._device_info
_ORIGINAL_CONTROLS_SYNC = camera._controls_sync
_ORIGINAL_SET_CONTROL_SYNC = camera._set_control_sync
_INSTALLED = False


def _read_text(path: Path) -> str | None:
    try:
        value = path.read_text(encoding="utf-8", errors="replace").strip()
    except OSError:
        return None
    return value or None


def _usb_identity(device: str) -> dict[str, Any]:
    """Find the USB parent of /dev/videoX and return stable descriptor data."""
    name = Path(device).name
    node = Path("/sys/class/video4linux") / name / "device"
    try:
        node = node.resolve(strict=True)
    except OSError:
        return {}

    for parent in (node, *node.parents):
        vendor = _read_text(parent / "idVendor")
        product = _read_text(parent / "idProduct")
        if vendor and product:
            revision = _read_text(parent / "bcdDevice")
            return {
                "usb_vendor_id": vendor.lower(),
                "usb_product_id": product.lower(),
                "usb_device_revision": revision,
                # bcdDevice is the device release number reported by the USB
                # firmware. We expose it explicitly rather than inventing a
                # vendor firmware version that Linux cannot reliably query.
                "firmware_revision": revision,
                "usb_manufacturer": _read_text(parent / "manufacturer"),
                "usb_product": _read_text(parent / "product"),
                "usb_serial": _read_text(parent / "serial"),
            }
    return {}


def _parse_v4l2_led_control(device: str) -> dict[str, Any] | None:
    try:
        result = camera._run(["v4l2-ctl", "--device", device, "--list-ctrls-menus"], timeout=6)
    except (OSError, TimeoutError):
        return None
    if result.returncode != 0:
        return None
    text = (result.stdout + b"\n" + result.stderr).decode("utf-8", errors="replace")
    for line in text.splitlines():
        match = camera.CONTROL_RE.match(line)
        if not match:
            continue
        name, kind, rest = match.groups()
        lower = name.lower()
        if lower not in _NATIVE_LED_NAMES and not ("led" in lower and "mode" in lower):
            continue
        pairs = {key: int(value) for key, value in camera.PAIR_RE.findall(rest)}
        flags: list[str] = []
        if "flags=" in rest:
            flags = [item.strip() for item in rest.split("flags=", 1)[1].split(",") if item.strip()]
        return {
            "method": "v4l2",
            "native_control": name,
            "native_type": kind.strip(),
            "native_value": pairs.get("value"),
            "writable": not any(flag in {"read-only", "inactive", "disabled"} for flag in flags),
        }
    return None


def _uvcdynctrl_led_control(device: str) -> dict[str, Any] | None:
    if not shutil.which("uvcdynctrl"):
        return None
    video = Path(device).name
    commands = [
        ["uvcdynctrl", "--device", video, "--clist"],
        ["uvcdynctrl", "-d", video, "-c"],
    ]
    for command in commands:
        try:
            result = camera._run(command, timeout=6)
        except (OSError, TimeoutError):
            continue
        text = (result.stdout + b"\n" + result.stderr).decode("utf-8", errors="replace")
        if result.returncode == 0 and re.search(r"\bLED1 Mode\b", text, re.IGNORECASE):
            current = None
            try:
                get_result = camera._run(["uvcdynctrl", "-d", video, "-g", "LED1 Mode"], timeout=6)
                if get_result.returncode == 0:
                    number = re.search(r"-?\d+", get_result.stdout.decode("utf-8", errors="replace"))
                    current = int(number.group(0)) if number else None
            except OSError:
                pass
            return {
                "method": "uvcdynctrl",
                "native_control": "LED1 Mode",
                "native_value": current,
                "writable": True,
            }
    return None


def _capability(device: str, row: dict[str, Any] | None = None) -> dict[str, Any]:
    identity = _usb_identity(device)
    row = row or {}
    descriptor = " ".join(str(value or "") for value in (
        identity.get("usb_manufacturer"), identity.get("usb_product"),
        row.get("name"), row.get("card"),
    )).lower()
    vendor = str(identity.get("usb_vendor_id") or "").lower()
    c920_family = vendor == "046d" and ("c920" in descriptor or bool(row.get("c920_match")))

    native = _parse_v4l2_led_control(device)
    if native is None and (vendor == "046d" or c920_family):
        native = _uvcdynctrl_led_control(device)

    supported = bool(native and native.get("writable"))
    return {
        **identity,
        "detected_model": identity.get("usb_product") or row.get("name") or row.get("card"),
        "c920_family": c920_family,
        "led_supported": supported,
        "led_method": native.get("method") if native else None,
        "led_native_control": native.get("native_control") if native else None,
        "led_native_value": native.get("native_value") if native else None,
        "led_reason": (
            "LED-Control vom Gerät bestätigt" if supported else
            "Kamera/Firmware meldet keinen beschreibbaren LED-Control"
        ),
    }


def _device_info(camera_id: str, device: str) -> dict[str, Any]:
    row = _ORIGINAL_DEVICE_INFO(camera_id, device)
    cap = _capability(device, row)
    row.update({
        key: value for key, value in cap.items()
        if key not in {"led_native_value"}
    })
    return row


def _virtual_control(cap: dict[str, Any]) -> dict[str, Any]:
    native = cap.get("led_native_value")
    # Auto (3) oder On (1) gelten in der GUI als LED aktiv; Off (0) als aus.
    value = 0 if native == 0 else 1
    return {
        "name": VIRTUAL_LED_CONTROL,
        "type": "bool",
        "min": 0,
        "max": 1,
        "step": 1,
        "default": 1,
        "value": value,
        "flags": [],
        "menu": [],
        "writable": True,
    }


def _controls_sync(camera_id: str | None) -> dict[str, Any]:
    data = _ORIGINAL_CONTROLS_SYNC(camera_id)
    devices, _ignored = camera._discover_devices_sync()
    row = next((item for item in devices if item.get("id") == data["camera_id"]), {})
    cap = _capability(data["device"], row)

    # Native LED-Regler werden durch einen stabilen booleschen Grow-Central-
    # Regler ersetzt. Dadurch bleibt die GUI unabhängig von Hersteller-Namen.
    controls = [
        item for item in data.get("controls", [])
        if item.get("name", "").lower() not in _NATIVE_LED_NAMES
        and not ("led" in item.get("name", "").lower() and "mode" in item.get("name", "").lower())
    ]
    if cap["led_supported"]:
        controls.append(_virtual_control(cap))
    return {**data, "controls": controls, "led_capability": cap}


def _set_led(camera_id: str, value: int) -> dict[str, Any]:
    if value not in (0, 1):
        raise ValueError("Kamera_LED akzeptiert nur 0 oder 1")
    resolved_id, device = camera._resolve_camera(camera_id)
    devices, _ignored = camera._discover_devices_sync()
    row = next((item for item in devices if item.get("id") == resolved_id), {})
    cap = _capability(device, row)
    if not cap["led_supported"]:
        raise ValueError("LED-Steuerung wird von dieser Kamera/Firmware nicht unterstützt")

    # 3 = Auto (LED folgt dem Stream), 0 = dauerhaft aus. Das ist für eine
    # Webcam sinnvoller als 'dauerhaft an' und entspricht Logitechs LED1 Mode.
    native_value = 3 if value else 0
    if cap["led_method"] == "v4l2":
        result = camera._run([
            "v4l2-ctl", "--device", device, "--set-ctrl",
            f'{cap["led_native_control"]}={native_value}',
        ], timeout=8)
    elif cap["led_method"] == "uvcdynctrl":
        result = camera._run([
            "uvcdynctrl", "-d", Path(device).name, "-s", "LED1 Mode", str(native_value),
        ], timeout=8)
    else:
        raise ValueError("Kein sicherer LED-Steuerweg für diese Kamera erkannt")

    text = (result.stdout + b"\n" + result.stderr).decode("utf-8", errors="replace")
    if result.returncode != 0:
        raise RuntimeError(text.strip()[:300] or "Kamera-LED konnte nicht gesetzt werden")

    refreshed = _capability(device, row)
    refreshed["led_native_value"] = native_value if refreshed.get("led_native_value") is None else refreshed["led_native_value"]
    return {
        "ok": True,
        "camera_id": resolved_id,
        "control": _virtual_control(refreshed),
        "auto_focus_disabled": False,
        "led_capability": refreshed,
    }


def _set_control_sync(request: camera.CameraControlRequest) -> dict[str, Any]:
    if request.control == VIRTUAL_LED_CONTROL:
        return _set_led(request.camera_id, request.value)
    return _ORIGINAL_SET_CONTROL_SYNC(request)


def install() -> None:
    """Install wrappers exactly once before the FastAPI app starts serving."""
    global _INSTALLED
    if _INSTALLED:
        return
    camera._device_info = _device_info
    camera._controls_sync = _controls_sync
    camera._set_control_sync = _set_control_sync
    # Existing discovery results may predate the wrappers.
    camera._DISCOVERY_CACHE = None
    _INSTALLED = True
