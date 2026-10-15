from pathlib import Path


def test_usb_ui_reestablishes_signed_identity_after_restart_without_writes():
    root = Path(__file__).resolve().parents[1]
    js = (root / "web/usb_onboarding.js").read_text(encoding="utf-8")
    html = (root / "web/platform.html").read_text(encoding="utf-8")
    assert "const autoInspected = new Set()" in js
    assert "device.state === 'DETECTED'" in js
    assert "+ '/inspect'" in js
    assert "method:'POST'" in js
    auto = js[js.index("// After a Pi/service reboot"):js.index("list.replaceChildren();", js.index("// After a Pi/service reboot"))]
    assert "/flash" not in auto
    assert "/network" not in auto
    assert "/assign" not in auto
    assert "usb_onboarding.js?v=20261015-usbid1" in html
