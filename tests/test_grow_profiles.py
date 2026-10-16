import asyncio

import pytest
from fastapi import HTTPException

import app.rooms as rooms


def _seed_room(tmp_path, monkeypatch):
    monkeypatch.setattr(rooms, "DATA_FILE", tmp_path / "rooms.json")
    state = rooms.empty_state()
    state["rooms"].append({"id": "room_1", "name": "Zelt 1"})
    rooms.save_state(state)


def _profile_body():
    return rooms.GrowProfileCreate(
        name="Standard Indoor",
        phases=[
            rooms.GrowProfilePhase(
                phase="vegetative",
                expected_days=28,
                targets=rooms.GrowTargets(vpd_kpa_min=0.8, vpd_kpa_max=1.2, ppfd_umol_m2_s_min=350, ppfd_umol_m2_s_max=650),
            ),
            rooms.GrowProfilePhase(
                phase="flowering",
                expected_days=63,
                targets=rooms.GrowTargets(vpd_kpa_min=1.1, vpd_kpa_max=1.5, dli_mol_m2_day_target=35),
            ),
        ],
    )


def test_profile_crud_and_assignment(tmp_path, monkeypatch):
    _seed_room(tmp_path, monkeypatch)
    profile = asyncio.run(rooms.create_grow_profile(_profile_body()))
    assert profile["name"] == "Standard Indoor"
    assert len(profile["phases"]) == 2

    plant = asyncio.run(rooms.create_plant("room_1", rooms.PlantCreate(
        name="Profilpflanze", start_date="2026-10-16", phase="vegetative", profile_id=profile["id"]
    )))
    assert plant["profile_id"] == profile["id"]

    with pytest.raises(HTTPException) as exc:
        asyncio.run(rooms.delete_grow_profile(profile["id"]))
    assert exc.value.status_code == 409


def test_unknown_profile_cannot_be_assigned(tmp_path, monkeypatch):
    _seed_room(tmp_path, monkeypatch)
    with pytest.raises(HTTPException) as exc:
        asyncio.run(rooms.create_plant("room_1", rooms.PlantCreate(name="Nope", profile_id="profile_missing")))
    assert exc.value.status_code == 404


def test_vpd_target_assessment():
    targets = {"vpd_kpa_min": 0.9, "vpd_kpa_max": 1.3}
    assert rooms.evaluate_vpd(0.7, targets)["status"] == "low"
    assert rooms.evaluate_vpd(1.1, targets)["status"] == "target"
    assert rooms.evaluate_vpd(1.6, targets)["status"] == "high"
    assert rooms.evaluate_vpd(None, targets)["status"] == "unknown"


def test_grow_status_uses_profile_phase_and_real_snapshot(tmp_path, monkeypatch):
    _seed_room(tmp_path, monkeypatch)
    profile = asyncio.run(rooms.create_grow_profile(_profile_body()))
    plant = asyncio.run(rooms.create_plant("room_1", rooms.PlantCreate(
        name="Statuspflanze", start_date="2026-10-16", phase="flowering", profile_id=profile["id"]
    )))
    with rooms.edit_state() as state:
        rooms.append_sensor(state, "room_1", {
            "temperature_c": 25.0,
            "humidity_percent": 55.0,
            "ppfd_umol_m2_s": 720.0,
            "source": "assigned-devices",
        })

    status = asyncio.run(rooms.plant_grow_status("room_1", plant["id"]))

    assert status["phase_profile"]["phase"] == "flowering"
    assert status["vpd"]["status"] in {"low", "target", "high"}
    assert status["sensor_snapshot"]["ppfd_umol_m2_s"] == 720.0
    assert status["harvest_window"]["forecast"] is True
    assert status["harvest_window"]["expected_harvest_from"] is not None
    assert status["harvest_window"]["expected_harvest_to"] is not None


def test_profile_range_validation_rejects_inverted_targets():
    with pytest.raises(ValueError):
        rooms.GrowTargets(vpd_kpa_min=1.5, vpd_kpa_max=1.0)
