from pathlib import Path


def test_setup_ap_is_permanently_display_free():
    script = Path("image-builder/firstboot/setup-ap.sh").read_text()
    assert "802-11-wireless-security.pmf 1" in script
    assert "display-policy" in script
    assert "display-setup.sh" not in script
    assert "chromium" not in script.lower()


def test_display_setup_enforces_headless_product_policy():
    script = Path("image-builder/firstboot/display-setup.sh").read_text()
    assert "headless controller" in script
    assert "display-policy" in script
    assert "grow-central-display-kiosk.service" in script
    assert "disable --now" in script
    assert "browser / mobile client" in script
    assert "1024x600" not in script
    assert "chromium" not in script.lower()
