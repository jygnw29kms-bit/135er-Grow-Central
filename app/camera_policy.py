"""Grow Central camera policy layered on top of the generic UVC backend.

The core camera module intentionally stays generic. This policy constrains the
Grow Central UI to Raspberry-Pi-friendly modes and exposes a guarded status-LED
control when the attached UVC device actually advertises one.
"""
from __future__ import annotations

from typing import Any

MAX_WIDTH = 1280
MAX_HEIGHT = 720
LED_CONTROL_CANDIDATES = (
    "led1_mode",
    "led_mode",
    "privacy_led",
    "privacy",
)


def install(camera_module: Any) -> None:
    if getattr(camera_module, "_GC_POLICY_INSTALLED", False):
        return

    original_parse_modes = camera_module._parse_mjpeg_modes
    original_resolve_mode = camera_module._resolve_capture_mode
    original_controls = camera_module._controls_sync
    original_set_control = camera_module._set_control_sync

    def parse_modes_720p(text: str):
        modes = original_parse_modes(text)
        return [
            mode
            for mode in modes
            if int(mode.get("width") or 0) <= MAX_WIDTH
            and int(mode.get("height") or 0) <= MAX_HEIGHT
        ]

    def resolve_mode_720p(camera_id, width, height):
        if width is not None and width > MAX_WIDTH:
            raise ValueError("Grow Central limits camera capture to 1280x720")
        if height is not None and height > MAX_HEIGHT:
            raise ValueError("Grow Central limits camera capture to 1280x720")
        return original_resolve_mode(camera_id, width, height)

    def controls_with_led(camera_id):
        payload = original_controls(camera_id)
        controls = payload.get("controls") or []
        led = next((row for row in controls if row.get("name") in LED_CONTROL_CANDIDATES), None)
        if led is not None:
            # Normalize the user-facing control without inventing support. The
            # underlying source control remains recorded for guarded writes.
            source_name = str(led.get("name"))
            led["source_name"] = source_name
            led["name"] = "status_led"
            led["type"] = "bool" if led.get("type") in {"bool", "boolean"} else led.get("type")
            payload["status_led_available"] = True
            payload["status_led_source"] = source_name
        else:
            payload["status_led_available"] = False
        payload["max_resolution"] = {"width": MAX_WIDTH, "height": MAX_HEIGHT, "label": "720p"}
        return payload

    def set_control_with_led(request):
        if request.control != "status_led":
            return original_set_control(request)
        raw = original_controls(request.camera_id)
        source = next(
            (row.get("name") for row in raw.get("controls") or [] if row.get("name") in LED_CONTROL_CANDIDATES),
            None,
        )
        if not source:
            raise ValueError("camera does not expose a software-controllable status LED")
        mapped = request.model_copy(update={"control": source})
        result = original_set_control(mapped)
        if result.get("control"):
            result["control"]["source_name"] = source
            result["control"]["name"] = "status_led"
        return result

    camera_module._parse_mjpeg_modes = parse_modes_720p
    camera_module._resolve_capture_mode = resolve_mode_720p
    camera_module._controls_sync = controls_with_led
    camera_module._set_control_sync = set_control_with_led
    camera_module._GC_POLICY_INSTALLED = True
