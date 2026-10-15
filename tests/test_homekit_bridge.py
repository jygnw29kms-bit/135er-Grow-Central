from __future__ import annotations

import asyncio
from pathlib import Path

from fastapi.responses import FileResponse

import app.homekit_bridge as homekit


def test_homekit_status_and_qr(tmp_path: Path, monkeypatch):
    status_file = tmp_path / "status.json"
    qr_file = tmp_path / "pairing.svg"
    status_file.write_text('{"running":true,"paired":false,"setup_code":"123-45-678","setup_uri":"X-HM://TEST"}', encoding="utf-8")
    qr_file.write_text('<svg xmlns="http://www.w3.org/2000/svg"></svg>', encoding="utf-8")
    monkeypatch.setattr(homekit, "STATUS_FILE", status_file)
    monkeypatch.setattr(homekit, "QR_FILE", qr_file)
    state = asyncio.run(homekit.homekit_status())
    assert state["available"] is True
    assert state["running"] is True
    assert state["paired"] is False
    assert state["setup_code"] == "123-45-678"
    response = asyncio.run(homekit.homekit_pairing_qr())
    assert isinstance(response, FileResponse)
    assert Path(response.path) == qr_file
    assert response.media_type == "image/svg+xml"


def test_homekit_final_master_ui_and_image_contract():
    root = Path(__file__).resolve().parents[1]
    html = (root / "web/platform.html").read_text(encoding="utf-8")
    js = (root / "web/platform-master.js").read_text(encoding="utf-8")
    css = (root / "web/platform-master.css").read_text(encoding="utf-8")
    workflow = (root / ".github/workflows/build-pi3-image.yml").read_text(encoding="utf-8")
    requirements = (root / "requirements.txt").read_text(encoding="utf-8")
    assert 'data-view="applehome"' in html
    assert 'id="homekitQr"' in html
    assert 'id="homekitCode"' in html
    assert "/api/v1/homekit/status" in js
    assert "/api/v1/homekit/pairing.svg" in js
    assert ".homekit-qr-card" in css
    assert "HAP-python[QRCode]==5.0.0" in requirements
    assert "grow-central-homekit.service" in workflow
    assert "ufw allow 51827/tcp" in workflow

def test_homekit_room_inventory_exports_only_real_measurements(monkeypatch):
    import app.rooms as rooms
    state={
        "rooms":[{"id":"r1","name":"Zelt"},{"id":"r2","name":"Leer"},{"id":"r3","name":"Nur Energie"}],
        "sensor_history":[
            {"room_id":"r1","temperature_c":24.5,"humidity_percent":58.0,"soil_moisture_percent":42.0},
            {"room_id":"r3","power_w":120.0},
        ],
    }
    monkeypatch.setattr(rooms,"load_state",lambda:state)
    rows=homekit._latest_room_values()
    assert len(rows)==1
    assert rows[0]["id"]=="r1"
    assert rows[0]["services"]==("temperature","humidity","soil_moisture")
    assert rows[0]["latest"]["temperature_c"]==24.5


def test_homekit_topology_signature_tracks_rooms_services_names_and_switches():
    from types import SimpleNamespace
    rooms=[{"id":"r1","name":"Zelt","services":("temperature",)}]
    switches=[SimpleNamespace(id="plug1",name="Lampe")]
    first=homekit._topology_signature(rooms,switches)
    assert first!=homekit._topology_signature([{"id":"r1","name":"Zelt","services":("temperature","humidity")}],switches)
    assert first!=homekit._topology_signature([{"id":"r1","name":"Growraum","services":("temperature",)}],switches)
    assert first!=homekit._topology_signature(rooms,[SimpleNamespace(id="plug2",name="Pumpe")])


def test_homekit_bridge_starts_child_tasks_and_reloads_changed_topology():
    source=Path("app/homekit_bridge.py").read_text(encoding="utf-8")
    assert "await super().run()" in source
    assert "_topology_signature() != self.topology_signature" in source
    assert "self.driver.stop()" in source
    assert "Restart=always" in Path(".github/workflows/build-pi3-image.yml").read_text(encoding="utf-8")
    assert "value=20.0" not in source and "value=50.0" not in source


def test_homekit_room_inventory_tolerates_short_metric_dropout(monkeypatch):
    import app.rooms as rooms
    state={
        "rooms":[{"id":"r1","name":"Zelt"}],
        "sensor_history":[
            {"room_id":"r1","temperature_c":24.0,"humidity_percent":55.0},
            {"room_id":"r1","temperature_c":24.3,"humidity_percent":None},
        ],
    }
    monkeypatch.setattr(rooms,"load_state",lambda:state)
    row=homekit._latest_room_values()[0]
    assert row["services"]==("temperature","humidity")
    assert row["latest"]["temperature_c"]==24.3
    assert row["latest"]["humidity_percent"]==55.0
