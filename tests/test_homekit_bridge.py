from __future__ import annotations

import asyncio
from datetime import datetime, timedelta, timezone
from pathlib import Path

from fastapi.responses import FileResponse

import app.homekit_bridge as homekit

NOW = datetime(2026, 10, 15, 18, 0, tzinfo=timezone.utc)

def ts(minutes=0):
    return (NOW - timedelta(minutes=minutes)).isoformat()


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
            {"room_id":"r1","timestamp":ts(),"temperature_c":24.5,"humidity_percent":58.0,"soil_moisture_percent":42.0,"soil_calibration_status":"valid"},
            {"room_id":"r3","timestamp":ts(),"power_w":120.0},
        ],
    }
    monkeypatch.setattr(rooms,"load_state",lambda:state)
    rows=homekit._latest_room_values(now=NOW)
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
            {"room_id":"r1","timestamp":ts(2),"temperature_c":24.0,"humidity_percent":55.0},
            {"room_id":"r1","timestamp":ts(),"temperature_c":24.3,"humidity_percent":None},
        ],
    }
    monkeypatch.setattr(rooms,"load_state",lambda:state)
    row=homekit._latest_room_values(now=NOW)[0]
    assert row["services"]==("temperature","humidity")
    assert row["latest"]["temperature_c"]==24.3
    assert row["latest"]["humidity_percent"]==55.0


def test_homekit_never_exports_stale_or_uncalibrated_soil(monkeypatch):
    import app.rooms as rooms
    state={
        "rooms":[{"id":"r1","name":"Zelt"},{"id":"r2","name":"Alt"}],
        "sensor_history":[
            {"room_id":"r1","timestamp":ts(),"temperature_c":24.0,"soil_moisture_percent":42.0,"soil_calibration_status":"required"},
            {"room_id":"r2","timestamp":ts(20),"temperature_c":25.0,"humidity_percent":60.0,"soil_moisture_percent":50.0,"soil_calibration_status":"valid"},
        ],
    }
    monkeypatch.setattr(rooms,"load_state",lambda:state)
    rows=homekit._latest_room_values(now=NOW)
    assert len(rows)==1
    assert rows[0]["id"]=="r1"
    assert rows[0]["services"]==("temperature",)
    assert "soil_moisture_percent" not in rows[0]["latest"]


def test_homekit_rejects_nonfinite_metrics(monkeypatch):
    import app.rooms as rooms
    state={
        "rooms":[{"id":"r1","name":"Zelt"}],
        "sensor_history":[{"room_id":"r1","timestamp":ts(),"temperature_c":float("nan"),"humidity_percent":58.0}],
    }
    monkeypatch.setattr(rooms,"load_state",lambda:state)
    row=homekit._latest_room_values(now=NOW)[0]
    assert row["services"]==("humidity",)
    assert "temperature_c" not in row["latest"]


def test_homekit_accessory_aids_are_stable_across_inventory_order():
    from types import SimpleNamespace
    room_a={"id":"room-a","name":"A","services":("temperature",)}
    room_b={"id":"room-b","name":"B","services":("humidity",)}
    switch_a=SimpleNamespace(id="plug-a",name="Lampe")
    switch_b=SimpleNamespace(id="plug-b",name="Pumpe")
    first=homekit._accessory_aids([room_a,room_b],[switch_a,switch_b])
    second=homekit._accessory_aids([room_b,room_a],[switch_b,switch_a])
    assert first==second
    assert len(set(first.values()))==4
    assert 1 not in first.values() and 7 not in first.values()


def test_homekit_text_and_stability_contract():
    source=Path("app/homekit_bridge.py").read_text(encoding="utf-8")
    assert "HOMEKIT_FRESH_SECONDS = 15 * 60" in source
    assert 'soil_calibration_status") == "valid"' in source
    assert "_accessory_aids" in source
    assert "ge?ndert" not in source
