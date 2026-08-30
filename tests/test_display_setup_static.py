from pathlib import Path


def test_setup_ap_is_permanently_display_free():
    script = Path("image-builder/firstboot/setup-ap.sh").read_text()
    assert "ipv4.method shared" in script
    assert "wifi-sec.psk" not in script
    assert "display-policy" in script
    assert "display-setup.sh" not in script
    assert "chromium" not in script.lower()


def test_display_setup_script_is_removed_from_headless_product():
    display_setup = Path("image-builder/firstboot/display-setup.sh")
    workflow = Path(".github/workflows/build-pi3-image.yml").read_text()
    setup_ap = Path("image-builder/firstboot/setup-ap.sh").read_text()
    assert not display_setup.exists()
    assert "test ! -e /opt/135er-grow-central/image-builder/firstboot/display-setup.sh" in workflow
    assert "Unexpected kiosk package in headless image" in workflow
    assert "display-policy" in setup_ap
