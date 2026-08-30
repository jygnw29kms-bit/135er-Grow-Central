from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_rooms_navigation_present():
    html = (ROOT / "web" / "console.html").read_text(encoding="utf-8")
    assert "RÄUME & GROW" in html
    assert "Raumübersicht" in html
    assert "Growtagebuch" in html
    assert "Pflanzen" in html


def test_room_api_is_wired_into_entrypoint():
    entry = (ROOT / "app" / "entrypoint.py").read_text(encoding="utf-8")
    assert "rooms_router" in entry
    assert "app.include_router(rooms_router)" in entry


def test_rooms_feature_does_not_remove_firstboot_network_path():
    setup_ap = (ROOT / "image-builder" / "firstboot" / "setup-ap.sh").read_text(encoding="utf-8")
    assert "grow-central-setup-ap" in setup_ap
    assert "ipv4.method shared" in setup_ap
    assert 'DHCP_RANGE="10.42.0.10,10.42.0.250"' in setup_ap
    assert "wifi-sec.psk" not in setup_ap
