"""Primary GrowCentral devices view exposes real, safe Pi Bluetooth scanning."""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_ble_scan_is_accessible_in_main_devices_view():
    html=(ROOT/"web/platform.html").read_text(encoding="utf-8")
    js=(ROOT/"web/platform.js").read_text(encoding="utf-8")
    assert 'id="bleDiscoverBtn"' in html
    assert 'id="bleDiscoveryStatus"' in html
    assert 'id="bleDiscoveryResults"' in html
    assert 'id="bleGattDetails"' in html
    assert "/api/mars-hydro/ble/scan" in js
    assert "/api/mars-hydro/ble/inspect" in js
    assert "bleDiscoverBtn')?.addEventListener('click',scanLocalBluetooth)" in js
    assert "device.mars_hydro_hint" in js
    assert "document.createElement('strong')" in js
    assert "inspectLocalBluetooth" in js
    assert "write_gatt_char" not in js
