"""Beta 1.0: real Pi persistence acknowledgment, Cloud room-scoping and no auto-retry."""
import asyncio
import json
from types import SimpleNamespace

import pytest

from local.cloud_link import remote_agent
from app import rooms


class WS:
    def __init__(self, requests):
        self.requests = requests
        self.out = []

    def __aiter__(self):
        async def itr():
            for req in self.requests:
                yield json.dumps(req)
        return itr()

    async def send(self, raw):
        self.out.append(json.loads(raw))


class Response:
    def __init__(self, body=None, status=200):
        self.body = body or {}
        self.status_code = status
        self.is_success = 200 <= status < 300

    def raise_for_status(self):
        if not self.is_success:
            raise RuntimeError(f"status_{self.status_code}")

    def json(self):
        return self.body


class Local:
    def __init__(self, *, persist=True, snapshot=True):
        self.entries = {}
        self.calls = []
        self.persist = persist
        self.snapshot = snapshot

    async def post(self, path, *, json, **kwargs):
        self.calls.append(("POST", path))
        entry = {"id": "entry_demo1", "room_id": "room_test", **json,
                 "sensor_snapshot": {"captured_at": "2026-11-16T18:40:00+00:00"} if self.snapshot else {}}
        if self.persist:
            self.entries[entry["id"]] = entry
        return Response(entry)

    async def get(self, path, **kwargs):
        self.calls.append(("GET", path))
        key = path.split("/")[-1]
        return Response(self.entries[key]) if key in self.entries else Response(status=404)

    async def put(self, path, *, json, **kwargs):
        self.calls.append(("PUT", path))
        entry_id = path.rsplit("/", 1)[-1]
        if entry_id not in self.entries:
            return Response(status=404)
        self.entries[entry_id].update(json)
        return Response(self.entries[entry_id])

    async def delete(self, path, **kwargs):
        self.calls.append(("DELETE", path))
        self.entries.pop(path.rsplit("/", 1)[-1], None)
        return Response({"ok": True})


def message(kind, **kwargs):
    return {"type": kind, "request_id": "r1", "room_id": "room_test",
            "confirm_write": True, **kwargs}


def test_cloud_create_has_persisted_snapshot_and_room_bound_readback(monkeypatch):
    monkeypatch.setattr(remote_agent, "local_headers", lambda: {})
    local = Local()
    ws = WS([message("journal_create", title="Test", text="Testwert",
                     category="defoliation", plant_id="plant_abc")])
    asyncio.run(remote_agent.serve(ws, local))
    assert ws.out[0]["ok"] is True
    assert ws.out[0]["verified"] is True
    assert ws.out[0]["snapshot_present"] is True
    assert ws.out[0]["entry_id"] == "entry_demo1"
    assert [call[0] for call in local.calls] == ["POST", "GET"]
    assert local.calls[1][1].endswith("/rooms/room_test/journal/entry_demo1")


@pytest.mark.parametrize("persist,snapshot", [(False, True), (True, False)])
def test_cloud_never_claims_success_without_persisted_snapshot(monkeypatch, persist, snapshot):
    monkeypatch.setattr(remote_agent, "local_headers", lambda: {})
    local = Local(persist=persist, snapshot=snapshot)
    ws = WS([message("journal_create", title="Test", text="", category="note", plant_id="plant_abc")])
    asyncio.run(remote_agent.serve(ws, local))
    assert ws.out[0]["ok"] is False
    assert ws.out[0]["no_retry"] is True
    assert len([c for c in local.calls if c[0] == "POST"]) == 1


def test_missing_plant_never_writes(monkeypatch):
    monkeypatch.setattr(remote_agent, "local_headers", lambda: {})
    local = Local()
    ws = WS([message("journal_create", title="Test", text="", category="note", plant_id=None)])
    asyncio.run(remote_agent.serve(ws, local))
    assert ws.out[0]["error"] == "invalid_journal_entry"
    assert not local.calls


def test_update_and_delete_require_scoped_persistence(monkeypatch):
    monkeypatch.setattr(remote_agent, "local_headers", lambda: {})
    local = Local()
    local.entries["entry_demo1"] = {
        "id": "entry_demo1", "room_id": "room_test", "plant_id": "plant_abc",
        "title": "Alt", "sensor_snapshot": {"captured_at": "2026-11-16T18:40:00+00:00"}}
    ws = WS([
        message("journal_update", entry_id="entry_demo1", title="Neu",
                text="Notiz", category="note", plant_id="plant_abc"),
        message("journal_delete", entry_id="entry_demo1"),
    ])
    asyncio.run(remote_agent.serve(ws, local))
    assert [x["ok"] for x in ws.out] == [True, True]
    assert ws.out[0]["operation"] == "update"
    assert ws.out[1]["operation"] == "delete"
    assert [c[0] for c in local.calls] == ["PUT", "GET", "DELETE", "GET"]


def test_single_entry_cloud_read_is_allowlisted_but_cross_paths_are_not(monkeypatch):
    monkeypatch.setattr(remote_agent, "local_headers", lambda: {})
    local = Local()
    local.entries["entry_demo1"] = {"id": "entry_demo1", "room_id": "room_test"}
    ws = WS([
        {"type": "read", "request_id": "r1", "path": "/api/v1/rooms/room_test/journal/entry_demo1"},
        {"type": "read", "request_id": "r2", "path": "/api/v1/rooms/room_test/journal/../../admin"},
        {"type": "read", "request_id": "r3", "path": "/api/v1/rooms/room_test/journal/entry_demo1?secret=1"},
    ])
    asyncio.run(remote_agent.serve(ws, local))
    assert ws.out[0]["ok"] is True
    assert [x["error"] for x in ws.out[1:]] == ["path_not_allowed", "path_not_allowed"]
    assert len(local.calls) == 1


def test_single_entry_api_never_returns_another_rooms_data(tmp_path, monkeypatch):
    monkeypatch.setattr(rooms, "DATA_FILE", tmp_path / "rooms.json")
    state = rooms.empty_state()
    state["rooms"] = [{"id": "room_test", "name": "Zelt"}, {"id": "room_other", "name": "Anders"}]
    state["room_journal"] = [{"id": "entry_demo1", "room_id": "room_test", "title": "Privat"}]
    rooms.save_state(state)
    found = asyncio.run(rooms.room_journal_entry("room_test", "entry_demo1"))
    assert found["title"] == "Privat"
    with pytest.raises(Exception):
        asyncio.run(rooms.room_journal_entry("room_other", "entry_demo1"))
