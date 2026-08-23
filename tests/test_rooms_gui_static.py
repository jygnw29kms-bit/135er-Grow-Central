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


def test_build85_network_path_not_touched_by_rooms_feature():
    setup_ap = (ROOT / "image-builder" / "firstboot" / "setup-ap.sh").read_text(encoding="utf-8")
    assert "802-11-wireless-security.pmf 1" in setup_ap
    assert "grow-central-setup-ap" in setup_ap
