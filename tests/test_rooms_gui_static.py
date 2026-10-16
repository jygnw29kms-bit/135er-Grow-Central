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


def test_room_views_show_substrate_moisture():
    js = (ROOT / "web" / "room_views.js").read_text(encoding="utf-8")
    assert "soil_moisture_percent" in js
    assert "Frischsubstrat" in js
    assert "soil_substrate_index_percent" in js
    assert r"Dreipunkt-Kalibrierung g\u00fcltig" in js


def test_console_uses_calibrated_three_point_soil_display():
    js = (ROOT / "web" / "console.js").read_text(encoding="utf-8")
    assert "soilHistoryValid" in js
    assert "soilHistoryDetail" in js
    assert "Frischsubstrat-Index" in js
    assert "soil_substrate_state" in js


def test_room_overview_hides_uncalibrated_soil_percentage():
    room_js = (ROOT / "web" / "room_views.js").read_text(encoding="utf-8")
    console_js = (ROOT / "web" / "console.js").read_text(encoding="utf-8")
    assert "soilValid(s)?`Bodenfeuchte:" in room_js
    assert "soilHistoryValid(s)?Number(s.soil_moisture_percent)" in console_js
    assert "Kalibrierung erforderlich" in room_js
    assert "Kalibrierung erforderlich" in console_js
