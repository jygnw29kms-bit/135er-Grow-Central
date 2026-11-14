"""Room-only Growbook: complete plant context and phase climate safety."""
import asyncio
from datetime import datetime, timedelta, timezone
import pytest
from fastapi import HTTPException
from app import rooms

@pytest.fixture
def setup(tmp_path, monkeypatch):
    monkeypatch.setattr(rooms, "DATA_FILE", tmp_path / "rooms.json")
    s=rooms.empty_state()
    s["rooms"]=[{"id":"r1","name":"Testzelt"}]
    rooms.save_state(s)
    return s

def make_plant(**overrides):
    values={"name":"Pflanze 1","crop":"Cannabis","phase":"vegetative",
      "substrate_type":"peat_mix","substrate_components":"Torf 60 %, Perlit 30 %, Kompost 10 %",
      "substrate_pre_fertilized":"yes","nutrition_plan":"organic","container_type":"plastic",
      "container_volume_l":20}
    values.update(overrides)
    return rooms.PlantCreate(**values)

def test_room_journal_requires_plant_and_complete_profile(setup):
    with pytest.raises(HTTPException) as error:
        asyncio.run(rooms.add_room_journal("r1",rooms.JournalEntry(title="Test")))
    assert error.value.status_code==422
    assert not rooms.load_state()["room_journal"]
    incomplete=asyncio.run(rooms.create_plant("r1",rooms.PlantCreate(name="Altbestand")))
    with pytest.raises(HTTPException) as error:
        asyncio.run(rooms.add_room_journal("r1",rooms.JournalEntry(title="Test",plant_id=incomplete["id"])))
    assert error.value.status_code==422
    full=asyncio.run(rooms.create_plant("r1",make_plant()))
    result=asyncio.run(rooms.add_room_journal("r1",rooms.JournalEntry(title="Test",plant_id=full["id"])))
    assert result["plant_phase"]=="vegetative"
    assert result["plant_id"]==full["id"]

def test_phase_climate_has_freshness_and_source_guard(setup):
    plant=asyncio.run(rooms.create_plant("r1",make_plant()))
    state=rooms.load_state()
    profiles={p["id"]:p for p in state["grow_profiles"]}
    fresh={"timestamp":datetime.now(timezone.utc).isoformat(),"temperature_c":24.0,"humidity_percent":60.0}
    x=rooms._climate_judgement(plant,fresh,profiles)
    assert x["status"]=="target"
    assert x["source"]=="cannabis_orientation"
    assert len([v for v in x["metrics"] if v["status"]=="target"])==2
    old={**fresh,"timestamp":(datetime.now(timezone.utc)-timedelta(hours=3)).isoformat()}
    assert rooms._climate_judgement(plant,old,profiles)["status"]=="stale"
    no_custom=rooms._climate_judgement({**plant,"crop":"Basilikum"},fresh,profiles)
    assert no_custom["status"]=="unrated"
    assert no_custom["source"]=="not_configured"

def test_named_growth_profile_overrides_orientation(setup):
    plant=asyncio.run(rooms.create_plant("r1",make_plant()))
    plant["profile_id"]="pr1"
    profiles={"pr1":{"phases":[{"phase":"vegetative","targets":{
        "temperature_c_min":18,"temperature_c_max":20,
        "humidity_percent_min":40,"humidity_percent_max":50}}]}}
    snapshot={"timestamp":datetime.now(timezone.utc).isoformat(),"temperature_c":24,"humidity_percent":60}
    evaluated=rooms._climate_judgement(plant,snapshot,profiles)
    assert evaluated["source"]=="grow_profile"
    assert evaluated["status"]=="warning"
    assert any(x["metric"]=="temperature_c" and x["status"]=="high" for x in evaluated["metrics"])
