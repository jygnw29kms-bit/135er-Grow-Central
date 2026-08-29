from pathlib import Path

from app.gui_shell import router as gui_router


ROOT = Path(__file__).resolve().parents[1]


def read(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


def test_dedicated_mobile_route_exists():
    paths = {route.path for route in gui_router.routes}
    assert "/mobile" in paths


def test_desktop_ui_has_simple_and_advanced_modes():
    html = read("web/platform.html")
    js = read("web/platform.js")
    assert 'id="simpleMode"' in html
    assert 'id="advancedMode"' in html
    assert "localStorage.setItem('gc.mode'" in js
    assert "/api/devices/discover?timeout=5" in js
    assert "/api/devices/runtime" in js


def test_mobile_ui_is_separate_and_uses_universal_device_api():
    html = read("web/mobile.html")
    js = read("web/mobile.js")
    assert 'class="bottom-nav"' in html
    assert 'id="mSimple"' in html
    assert 'id="mAdvanced"' in html
    assert "/api/devices/discover?timeout=5" in js
    assert "/api/devices/runtime" in js


def test_room_views_use_real_room_api_and_no_demo_metrics():
    room_js = read("web/room_views.js")
    desktop = read("web/platform.html")
    mobile = read("web/mobile.html")
    assert "/api/v1/rooms" in room_js
    assert 'id="temp">—<' in desktop
    assert 'id="mTemp">—<' in mobile
    assert "room_views.js" in desktop
    assert "room_views.js" in mobile


def test_capacitor_launcher_targets_mobile_route():
    launcher = read("mobile/www/app.js")
    assert "url.pathname = '/mobile'" in launcher
