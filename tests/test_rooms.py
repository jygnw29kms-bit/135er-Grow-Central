from pathlib import Path
import asyncio

import app.rooms as rooms


def test_vpd_calculation_is_plausible():
    value = rooms.calc_vpd(25.0, 60.0)
    assert value is not None
    assert 1.2 < value < 1.4


def test_rooms_state_roundtrip(tmp_path, monkeypatch):
    target = tmp_path / "rooms.json"
    monkeypatch.setattr(rooms, "DATA_FILE", target)
    state = rooms.empty_state()
    state["rooms"].append({"id": "room_test", "name": "Zelt 1"})
    state["assignments"]["plug_1"] = "room_test"
    rooms.save_state(state)
    loaded = rooms.load_state()
    assert loaded["rooms"][0]["name"] == "Zelt 1"
    assert loaded["assignments"]["plug_1"] == "room_test"
    assert target.stat().st_mode & 0o777 == 0o600


def test_sensor_sample_gets_vpd_and_room_id(tmp_path, monkeypatch):
    monkeypatch.setattr(rooms, "DATA_FILE", tmp_path / "rooms.json")
    state = rooms.empty_state()
    row = rooms.append_sensor(state, "room_1", {"temperature_c": 24.0, "humidity_percent": 55.0, "source": "test"})
    assert row["room_id"] == "room_1"
    assert row["vpd_kpa"] is not None
    assert state["sensor_history"][0]["source"] == "test"


def test_console_contains_room_navigation():
    html = Path("web/console.html").read_text(encoding="utf-8")
    assert "RÄUME & GROW" in html
    assert "Geräte zuordnen" in html
    assert "Growtagebuch" in html
    assert "Pflanzen" in html


async def _soil_device_overview(*, refresh: bool):
    return {
        "devices": [
            {
                "id": "growcentral_esp32:gc-soil-test",
                "online": True,
                "state": {"soil_moisture": 42.5, "soil_substrate_reference_percent": 67.3, "soil_substrate_index_percent": 63.15, "soil_substrate_delta_pp": -24.8},
            }
        ]
    }


def test_room_capture_includes_assigned_soil_moisture(tmp_path, monkeypatch):
    monkeypatch.setattr(rooms, "DATA_FILE", tmp_path / "rooms.json")
    async def legacy_overview(*, refresh): return {"devices": []}
    async def verified_native(timeout): return (await _soil_device_overview(refresh=False))["devices"]
    monkeypatch.setattr(rooms, "device_overview", legacy_overview)
    monkeypatch.setattr(rooms, "_native_gc_devices", verified_native)
    state = rooms.empty_state()
    state["rooms"].append({"id": "room_soil", "name": "Zelt Soil"})
    state["assignments"]["growcentral_esp32:gc-soil-test"] = "room_soil"
    rooms.save_state(state)

    captured = asyncio.run(rooms.capture_room_sensors_once())

    assert captured == 1
    saved = rooms.load_state()
    assert saved["sensor_history"][-1]["soil_moisture_percent"] == 42.5
    assert saved["sensor_history"][-1]["soil_substrate_reference_percent"] == 67.3
    assert saved["sensor_history"][-1]["soil_substrate_index_percent"] == 63.15
    assert saved["sensor_history"][-1]["soil_substrate_delta_pp"] == -24.8
    assert saved["sensor_history"][-1]["source"] == "assigned-devices"


async def _native_soil_nodes(timeout: float = 1.0):
    return [
        {
            "id": "growcentral_esp32:gc-soil-native",
            "name": "Grow-Central Soil Sensor",
            "adapter": "growcentral_esp32",
            "provider_id": "growcentral_esp32",
            "native_id": "gc-soil-native",
            "online": True,
            "state": {"soil_moisture": 37.2},
            "metadata": {"firmware": "0.2.0"},
        }
    ]


def test_room_devices_includes_native_gc_soil_node(tmp_path, monkeypatch):
    monkeypatch.setattr(rooms, "DATA_FILE", tmp_path / "rooms.json")
    monkeypatch.setenv("GC_SMARTHOME_DEVICE_CONFIG", str(tmp_path / "devices.json"))
    monkeypatch.setattr(rooms, "_native_gc_devices", _native_soil_nodes)
    state = rooms.empty_state()
    state["rooms"].append({"id": "room_native", "name": "Zelt Native"})
    rooms.save_state(state)

    payload = asyncio.run(rooms.room_devices("room_native"))

    assert payload["devices"][0]["id"] == "growcentral_esp32:gc-soil-native"
    assert payload["devices"][0]["adapter"] == "growcentral_esp32"


def test_native_gc_soil_node_can_be_assigned_to_room(tmp_path, monkeypatch):
    from types import SimpleNamespace
    monkeypatch.setattr(rooms, "TrustStore", lambda: SimpleNamespace(require_trusted=lambda _id: {"status": "TRUSTED"}))
    monkeypatch.setattr(rooms, "DATA_FILE", tmp_path / "rooms.json")
    monkeypatch.setenv("GC_SMARTHOME_DEVICE_CONFIG", str(tmp_path / "devices.json"))
    monkeypatch.setattr(rooms, "_native_gc_devices", _native_soil_nodes)
    state = rooms.empty_state()
    state["rooms"].append({"id": "room_native", "name": "Zelt Native"})
    rooms.save_state(state)

    result = asyncio.run(rooms.assign_device(
        "room_native",
        rooms.DeviceAssignment(device_id="growcentral_esp32:gc-soil-native"),
    ))

    assert result["ok"] is True
    assert rooms.load_state()["assignments"]["growcentral_esp32:gc-soil-native"] == "room_native"


def test_sensor_csv_exports_distinct_soil_reference_fields(tmp_path, monkeypatch):
    monkeypatch.setattr(rooms, "DATA_FILE", tmp_path / "rooms.json")
    state=rooms.empty_state()
    state["rooms"].append({"id":"room_csv","name":"CSV"})
    rooms.append_sensor(state,"room_csv",{
        "soil_moisture_percent":42.5,
        "soil_substrate_reference_percent":67.3,
        "soil_substrate_index_percent":63.15,
        "soil_substrate_delta_pp":-24.8,
        "soil_calibration_status":"valid",
        "source":"test",
    })
    rooms.save_state(state)
    response=asyncio.run(rooms.export_sensor_history("room_csv",5000))
    text=response.body.decode("utf-8")
    assert "soil_moisture_percent" in text
    assert "soil_substrate_reference_percent" in text
    assert "soil_substrate_index_percent" in text
    assert "soil_substrate_delta_pp" in text
    assert "42.5" in text and "67.3" in text and "63.15" in text and "-24.8" in text
