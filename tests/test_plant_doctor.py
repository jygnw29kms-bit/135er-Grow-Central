import asyncio

import app.rooms as rooms


def _seed(tmp_path, monkeypatch):
    monkeypatch.setattr(rooms, "DATA_FILE", tmp_path / "rooms.json")
    state = rooms.empty_state()
    state["rooms"].append({"id": "room_1", "name": "Zelt 1"})
    rooms.save_state(state)


def test_rule_doctor_uses_sensor_supported_vpd_and_soil_findings(tmp_path, monkeypatch):
    _seed(tmp_path, monkeypatch)
    profile = asyncio.run(rooms.create_grow_profile(rooms.GrowProfileCreate(
        name="Doctor profile",
        phases=[rooms.GrowProfilePhase(
            phase="vegetative",
            targets=rooms.GrowTargets(vpd_kpa_min=0.8, vpd_kpa_max=1.2),
        )],
    )))
    plant = asyncio.run(rooms.create_plant("room_1", rooms.PlantCreate(
        name="Plant A", phase="vegetative", profile_id=profile["id"]
    )))
    with rooms.edit_state() as state:
        rooms.append_sensor(state, "room_1", {
            "temperature_c": 30.0,
            "humidity_percent": 35.0,
            "soil_moisture_percent": 15.0,
            "source": "assigned-devices",
        })

    result = asyncio.run(rooms.diagnose_plant(
        "room_1",
        plant["id"],
        rooms.PlantDiagnosisRequest(symptoms=["yellowing"], affected_zone="lower", medium="soil"),
    ))

    codes = {row["code"] for row in result["findings"]}
    assert "environment_vpd_high" in codes
    assert "soil_moisture_low" in codes
    assert "symptom_chlorosis" in codes
    assert "keine sichere Diagnose" in result["disclaimer"]
    assert result["event_id"]
    event = rooms.load_state()["grow_events"][-1]
    assert event["type"] == "diagnosis"
    assert event["source"] == "plant-doctor"


def test_rule_doctor_returns_insufficient_instead_of_fake_certainty():
    findings = rooms.diagnose_plant_health(
        symptoms=[], affected_zone="unknown", medium="", snapshot={}, targets={}
    )
    assert len(findings) == 1
    assert findings[0]["code"] == "insufficient_evidence"
    assert findings[0]["confidence"] == "insufficient"


def test_diagnosis_can_run_without_saving_event(tmp_path, monkeypatch):
    _seed(tmp_path, monkeypatch)
    plant = asyncio.run(rooms.create_plant("room_1", rooms.PlantCreate(name="Plant B")))
    before = len(rooms.load_state()["grow_events"])

    result = asyncio.run(rooms.diagnose_plant(
        "room_1",
        plant["id"],
        rooms.PlantDiagnosisRequest(symptoms=["drooping"], save_event=False),
    ))

    assert "event_id" not in result
    assert len(rooms.load_state()["grow_events"]) == before
    assert any(row["code"] == "symptom_droop" for row in result["findings"])
