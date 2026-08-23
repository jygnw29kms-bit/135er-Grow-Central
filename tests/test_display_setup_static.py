from pathlib import Path


def test_display_setup_keeps_ap_failure_isolated():
    script = Path("image-builder/firstboot/setup-ap.sh").read_text()
    assert "display-setup.sh || log" in script
    assert "802-11-wireless-security.pmf 1" in script


def test_display_setup_has_elecrow_modes_and_console_status():
    script = Path("image-builder/firstboot/display-setup.sh").read_text()
    assert "1024x600" in script
    assert "800x480" in script
    assert "systemd.show_status=true" in script
    assert "/dev/tty1" in script
    assert "disable_overscan=1" in script
