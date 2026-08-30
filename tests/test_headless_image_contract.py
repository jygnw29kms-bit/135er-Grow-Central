from pathlib import Path


def test_final_image_prunes_graphical_kiosk_stack():
    smoke = Path("image-builder/firstboot/cloud-smoke-test.sh").read_text(encoding="utf-8")
    assert "HEADLESS-PRUNE" in smoke
    for package in ("chromium", "openbox", "xserver-xorg-core", "xinit"):
        assert package in smoke
    assert "apt-get purge" in smoke
    assert "display-policy" in smoke
    assert "command -v \"$command\"" in smoke


def test_production_entrypoint_has_no_touch_rewriter():
    entry = Path("app/entrypoint.py").read_text(encoding="utf-8")
    assert "TouchKeyboardMiddleware" not in entry
    assert "runtime_health_router" in entry
