"""Grow Central camera policy layered on top of the generic UVC backend.

The core camera module intentionally stays generic. This policy constrains the
Grow Central UI according to the canonical Raspberry Pi hardware profile and
exposes a guarded status-LED control when the attached UVC device advertises one.
"""
from __future__ import annotations

from typing import Any

from shared.hardware_profile import current_profile

LED_CONTROL_CANDIDATES = (
    "led1_mode",
    "led_mode",
    "privacy_led",
)


def install(camera_module: Any) -> None:
    if getattr(camera_module, "_GC_POLICY_INSTALLED", False):
        return

    profile = current_profile()
    max_width = profile.camera_max_width
    max_height = profile.camera_max_height

    original_parse_modes = camera_module._parse_mjpeg_modes
    original_resolve_mode = camera_module._resolve_capture_mode
    original_controls = camera_module._controls_sync
    original_set_control = camera_module._set_control_sync

    def parse_modes_profiled(text: str):
        modes = original_parse_modes(text)
        return [
            mode
            for mode in modes
            if int(mode.get("width") or 0) <= max_width
            and int(mode.get("height") or 0) <= max_height
        ]

    def resolve_mode_profiled(camera_id, width, height):
        limit = f"{max_width}x{max_height}"
        if width is not None and width > max_width:
            raise ValueError(f"Grow Central hardware profile limits camera resolution to {limit}")
        if height is not None and height > max_height:
            raise ValueError(f"Grow Central hardware profile limits camera resolution to {limit}")
        return original_resolve_mode(camera_id, width, height)

    def controls_with_led(camera_id):
        payload = original_controls(camera_id)
        controls = payload.get("controls") or []
        led = next((row for row in controls if row.get("name") in LED_CONTROL_CANDIDATES), None)
        if led is not None:
            source_name = str(led.get("name"))
            led["source_name"] = source_name
            led["name"] = "status_led"
            payload["status_led_available"] = True
            payload["status_led_source"] = source_name
        else:
            payload["status_led_available"] = False
        payload["max_resolution"] = {
            "width": max_width,
            "height": max_height,
            "label": f"{max_height}p",
        }
        payload["hardware_profile"] = profile.key
        payload["support_class"] = profile.support_class
        return payload

    def set_control_with_led(request):
        if request.control != "status_led":
            return original_set_control(request)

        raw = original_controls(request.camera_id)
        control = next(
            (row for row in raw.get("controls") or [] if row.get("name") in LED_CONTROL_CANDIDATES),
            None,
        )
        if not control:
            raise ValueError("camera does not expose a software-controllable status LED")
        if not control.get("writable"):
            raise PermissionError("camera status LED control is read-only or inactive")

        value = int(request.value)
        minimum, maximum = control.get("min"), control.get("max")
        if minimum is not None and value < minimum:
            raise ValueError(f"value below minimum {minimum}")
        if maximum is not None and value > maximum:
            raise ValueError(f"value above maximum {maximum}")
        menu = control.get("menu") or []
        if menu and value not in {item.get("value") for item in menu}:
            raise ValueError("invalid LED menu value")

        source = str(control["name"])
        result = camera_module._run(
            ["v4l2-ctl", "--device", raw["device"], "--set-ctrl", f"{source}={value}"],
            timeout=8,
        )
        text = (result.stdout + b"\n" + result.stderr).decode("utf-8", errors="replace")
        if result.returncode != 0:
            raise RuntimeError(text.strip()[:300] or "camera status LED write failed")

        refreshed = original_controls(request.camera_id)
        updated = next((row for row in refreshed.get("controls") or [] if row.get("name") == source), None)
        if updated:
            updated["source_name"] = source
            updated["name"] = "status_led"
        return {
            "ok": True,
            "camera_id": request.camera_id,
            "control": updated,
            "auto_focus_disabled": False,
        }

    camera_module._parse_mjpeg_modes = parse_modes_profiled
    camera_module._resolve_capture_mode = resolve_mode_profiled
    camera_module._controls_sync = controls_with_led
    camera_module._set_control_sync = set_control_with_led
    camera_module._GC_POLICY_INSTALLED = True
