"""Regression tests for the Pi-4 LAN-first boot and alpha service path."""
from pathlib import Path
from unittest.mock import patch
from types import SimpleNamespace

from app import firstboot
from app.mars_hydro import is_mars_hydro_ble_candidate, public_hardware_profile

ROOT = Path(__file__).resolve().parents[1]


def test_lan_status_is_independent_of_the_system_language():
    def fake_command(*args, **kwargs):
        assert args[-1] == "eth0"
        return SimpleNamespace(returncode=0, stdout="GENERAL.STATE:100 (verbunden)\nIP4.ADDRESS[1]:192.168.178.98/24\n")
    with patch.object(firstboot, "_command", fake_command):
        state = firstboot._device_state("eth0")
    assert state["connected"] is True
    assert "192.168.178.98/24" in state["addresses"]


def test_c260_is_only_an_unverified_vendor_app_alias():
    assert is_mars_hydro_ble_candidate("C260")
    profiles = public_hardware_profile()["authoritative_hardware"]
    fc = next(p for p in profiles if p["model"] == "FC3000")
    assert "C260" in fc["ble_observed_aliases"]
    assert fc["validated"] is False


def test_maintenance_persists_through_setup_and_access_point():
    root = ROOT / "image-builder/firstboot"
    apply = (root / "apply_setup.py").read_text(encoding="utf-8")
    ap = (root / "setup-ap.sh").read_text(encoding="utf-8")
    workflow = (ROOT / ".github/workflows/build-pi3-image.yml").read_text(encoding="utf-8")
    assert "MAINTENANCE_MARKER.is_file()" in apply
    assert "AllowUsers GrowCentral gcmaint" in apply
    assert "ensure_ethernet()" in apply
    assert "test-maintenance-enabled" in ap
    assert "systemctl enable --now ssh.service" in ap
    assert "gcmaint ALL=(ALL:ALL) NOPASSWD: ALL" in workflow
    assert "github.event_name == 'push'" in workflow
    assert 'image-builder/firstboot/test-maintenance.pub' in workflow


def test_lan_setup_shows_direct_ip_and_never_forces_captive_redirect():
    portal = (ROOT / "app/setup_portal.py").read_text(encoding="utf-8")
    assert "lanTransition" in portal
    assert "lanIPv4" in portal
    assert "successUrl()" in portal
    assert "Setup-WLAN verlassen" in portal
