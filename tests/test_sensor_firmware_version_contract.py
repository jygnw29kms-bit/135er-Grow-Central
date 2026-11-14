"""Prevent image builds from shipping mismatched USB and ESP32 firmware versions."""
from pathlib import Path
import re
import json

ROOT = Path(__file__).resolve().parents[1]


def test_compiled_sensor_firmware_version_matches_usb_flasher():
    cpp = (ROOT / "firmware/gc-soil-node/src/main.cpp").read_text(encoding="utf-8")
    usb = (ROOT / "app/provisioning/usb.py").read_text(encoding="utf-8")
    cpp_version = re.search(r'FW_VERSION\[\]\s*=\s*"([0-9.]+)"', cpp)
    usb_version = re.search(r"^VERSION\s*=\s*'([0-9.]+)'", usb, re.MULTILINE)
    assert cpp_version, "Sensor firmware version missing from main.cpp"
    assert usb_version, "USB provisioning firmware version missing"
    assert usb_version.group(1) == cpp_version.group(1), (
        f"USB flasher expects {usb_version.group(1)}, compiled firmware is "
        f"{cpp_version.group(1)}"
    )


def test_image_release_notes_match_sensor_version():
    cpp = (ROOT / "firmware/gc-soil-node/src/main.cpp").read_text(encoding="utf-8")
    version = re.search(r'FW_VERSION\[\]\s*=\s*"([0-9.]+)"', cpp).group(1)
    workflow = (ROOT / ".github/workflows/build-pi3-image.yml").read_text(encoding="utf-8")
    assert "python scripts/package-sensor-firmware.py" in workflow
    manifest = json.loads((ROOT / "firmware/gc-soil-node/dist/manifest.json").read_text(encoding="utf-8"))
    assert manifest["version"] == version
