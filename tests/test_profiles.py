import asyncio
import json
from pathlib import Path

from app import profiles

ROOT = Path(__file__).resolve().parents[1]


def test_profile_library_contains_general_crops_and_cannabis_without_cannabis_first_position():
    payload = json.loads((ROOT / "config" / "grow_profiles.json").read_text(encoding="utf-8"))
    ids = [row["id"] for row in payload["profiles"]]
    assert ids[:4] == ["tomato", "basil", "chili", "lettuce"]
    assert "cannabis" in ids


def test_profiles_have_phases_tasks_sources_and_systems():
    payload = json.loads((ROOT / "config" / "grow_profiles.json").read_text(encoding="utf-8"))
    for row in payload["profiles"]:
        assert row["name"]
        assert row["scientific_name"]
        assert row["systems"]
        assert row["sources"]
        assert row["phases"]
        assert all(phase.get("todos") for phase in row["phases"])


def test_profile_api_summary_and_checklist_are_readable():
    listing = asyncio.run(profiles.list_profiles(q=None))
    assert len(listing["profiles"]) >= 5
    checklist = asyncio.run(profiles.get_checklist("tomato"))
    assert checklist["printable"] is True
    assert len(checklist["tasks"]) >= 10


def test_profile_print_page_contains_checkboxes_and_print_action():
    response = asyncio.run(profiles.printable_profile("tomato"))
    body = response.body.decode("utf-8")
    assert "Grow-Central Basisprofil" in body
    assert "Drucken / als PDF speichern" in body
    assert 'class="box"' in body
