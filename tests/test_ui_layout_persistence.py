import os
from pathlib import Path

import pytest

from app import ui_layout


def sample_layout():
    return {
        "version": 2,
        "source": "grow-central-platform",
        "updatedAt": "2026-10-15T12:00:00Z",
        "shell": {"brand": "LOCAL-FIRST CONTROL CENTER", "sidebarWidth": 224, "gap": 10, "topbar": True, "sidebar": True, "rounded": True},
        "pages": [{
            "id": "overview", "label": "Uebersicht", "title": "Uebersicht", "icon": "+", "target": "overview",
            "parent": None, "visible": True, "advanced": False, "default": True,
            "widgets": [{"id": "metric-temp", "type": "metric", "title": "Temperatur", "kicker": "LIVE", "text": "Messwert", "width": 4, "height": "s", "binding": "temp", "visible": True, "advanced": False}],
        }],
    }


def test_layout_roundtrip_is_persistent(tmp_path, monkeypatch):
    target = tmp_path / "ui-layout.json"
    monkeypatch.setattr(ui_layout, "LAYOUT_FILE", target)
    clean = ui_layout.validate_layout(sample_layout())
    ui_layout.save_layout(clean)
    assert target.exists()
    if os.name != "nt":
        assert target.stat().st_mode & 0o777 == 0o640
    assert ui_layout.load_layout() == clean


def test_layout_rejects_invalid_geometry():
    layout = sample_layout()
    layout["pages"][0]["widgets"][0]["width"] = 13
    with pytest.raises(ValueError):
        ui_layout.validate_layout(layout)


def test_productive_ui_loads_layout_runtime_and_editor_uses_server_api():
    root = Path(__file__).resolve().parents[1]
    html = (root / "web/platform.html").read_text(encoding="utf-8")
    editor = (root / "web/ui-editor.js").read_text(encoding="utf-8")
    runtime = (root / "web/ui-layout-runtime.js").read_text(encoding="utf-8")
    assert "ui-layout-runtime.js" in html
    assert "fetch('/api/v1/ui-layout'" in editor
    assert "method:'PUT'" in editor
    assert "fetch('/api/v1/ui-layout'" in runtime
    assert "gridTemplateColumns='repeat(12,minmax(0,1fr))'" in runtime


def test_master_art_matches_accepted_final_master_crops():
    root = Path(__file__).resolve().parents[1] / "web"
    def jpeg_size(path):
        data = path.read_bytes()
        i = 2
        while i + 9 < len(data):
            if data[i] != 0xFF:
                i += 1
                continue
            marker = data[i + 1]
            if marker in {0xC0,0xC1,0xC2,0xC3,0xC5,0xC6,0xC7,0xC9,0xCA,0xCB,0xCD,0xCE,0xCF}:
                return int.from_bytes(data[i+5:i+7], 'big'), int.from_bytes(data[i+7:i+9], 'big')
            if marker in {0xD8,0xD9}:
                i += 2
                continue
            length = int.from_bytes(data[i+2:i+4], 'big')
            i += 2 + length
        raise AssertionError("JPEG size not found")
    hero_h, hero_w = jpeg_size(root / "master-grow-hero.jpg")
    room_h, room_w = jpeg_size(root / "master-grow-room.jpg")
    assert (hero_w, hero_h) == (470, 205)
    assert (room_w, room_h) == (350, 165)
