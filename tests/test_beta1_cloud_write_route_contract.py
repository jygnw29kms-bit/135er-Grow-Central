"""Regression contract for safe Cloud journal write-through and browser feedback."""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PORTAL = (ROOT / "cloud/portal/cloud-portal.js").read_text(encoding="utf-8")
CHILD = (ROOT / "cloud/portal/gc-final-cloud.js").read_text(encoding="utf-8")
AGENT = (ROOT / "local/cloud_link/remote_agent.py").read_text(encoding="utf-8")
ROOMS = (ROOT / "app/rooms.py").read_text(encoding="utf-8")


def test_creates_and_mutations_are_explicitly_approved():
    for value in ("journal_create", "journal_update", "journal_delete"):
        assert value in PORTAL
        assert value in AGENT
    assert "confirm_write:true" in PORTAL
    assert 'req.get("confirm_write") is True' in AGENT
    assert "new RegExp('^/api/v1/rooms/" in PORTAL


def test_parent_forwards_proof_not_just_a_generic_success():
    assert "verified:data.verified===true" in PORTAL
    assert "snapshot_present:data.snapshot_present===true" in PORTAL
    assert "operation:data.operation||'create'" in PORTAL
    assert "Schreibstatus unklar" in CHILD
    assert "Speicherstatus unklar" in CHILD


def test_pi_readback_requires_original_snapshot_and_room_scope():
    assert 'check=await local.get(LOCAL_API+path+"/"+entry_id' in AGENT
    assert 'saved.get("room_id")!=room_id' in AGENT
    assert 'saved.get("plant_id")!=plant_id' in AGENT
    assert 'saved.get("title")!=title.strip()' in AGENT
    assert 'not snapshot.get("captured_at")' in AGENT
    assert 'def room_journal_entry(room_id: str, entry_id: str)' in ROOMS


def test_cloud_disallows_unscoped_mutation_and_implicit_retries():
    assert "new RegExp('^/api/v1/rooms/(room_" in PORTAL
    assert "journal_delete_not_verified" in AGENT
    assert "no_retry" in AGENT
    assert "Kein automatischer Wiederholungsversuch" in PORTAL
