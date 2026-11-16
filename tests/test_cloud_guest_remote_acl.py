"""Cloud guest access and private reply isolation regression tests."""
import importlib.util
from pathlib import Path

import pytest

PATH = Path(__file__).resolve().parents[1] / "cloud/v7/guest_remote_acl.py"
spec = importlib.util.spec_from_file_location("gc_guest_remote_acl", PATH)
module = importlib.util.module_from_spec(spec)
import sys
sys.modules[spec.name] = module
spec.loader.exec_module(module)


def message(path="/api/v1/rooms/room_alpha/journal", request_id="same_id"):
    return {"type": "read", "request_id": request_id, "path": path}


def test_observer_can_read_only_explicit_room():
    request, reply = module.authorize_guest_message(
        message(), room_id="room_alpha", role="observer"
    )
    assert request["type"] == "read"
    assert reply == "read_result"
    with pytest.raises(module.GuestRequestDenied):
        module.authorize_guest_message(
            message("/api/v1/rooms/room_other/journal"), room_id="room_alpha",
            role="observer"
        )


@pytest.mark.parametrize("forbidden", [
    "/api/v1/rooms",
    "/api/v1/rooms/room_alpha",
    "/api/v1/rooms/room_alpha/journal?debug=1",
    "/api/v1/rooms/room_alpha/journal?limit=999",
    "/api/v1/rooms/room_alpha/../../../api/health",
    "/api/v1/camera/controls?camera_id=cam1",
    "/api/v1/rooms/room_alpha/journal%2Fextra",
    "/api/v1/history/points?room_id=room_alpha",
])
def test_forbidden_paths_never_forward(forbidden):
    with pytest.raises(module.GuestRequestDenied):
        module.authorize_guest_message(
            message(forbidden), room_id="room_alpha", role="grower"
        )


@pytest.mark.parametrize("kind", [
    "control", "room_create", "room_assign_device", "plant_create",
    "photo_create", "camera_frame", "photo_frame", "auth", "alarm_policy",
])
def test_guest_never_gets_owner_hardware_or_unscoped_commands(kind):
    with pytest.raises(module.GuestRequestDenied):
        module.authorize_guest_message(
            {"type": kind, "request_id": "a", "room_id": "room_alpha",
             "confirm_write": True}, room_id="room_alpha", role="admin"
        )


def test_journal_writes_only_for_authorized_growers_and_admins():
    event = {
        "type": "journal_create", "request_id": "entry1",
        "room_id": "room_alpha", "title": "Gegossen", "text": "Wasser",
        "category": "watering", "confirm_write": True,
    }
    for role in ("admin", "grower"):
        normalized, expected = module.authorize_guest_message(
            event, room_id="room_alpha", role=role
        )
        assert expected == "journal_result"
        assert normalized["room_id"] == "room_alpha"
    for role in ("observer", "owner", "unknown"):
        with pytest.raises(module.GuestRequestDenied):
            module.authorize_guest_message(event, room_id="room_alpha", role=role)
    with pytest.raises(module.GuestRequestDenied):
        module.authorize_guest_message(
            {**event, "room_id": "room_other"}, room_id="room_alpha", role="grower"
        )
    with pytest.raises(module.GuestRequestDenied):
        module.authorize_guest_message(
            {**event, "confirm_write": False}, room_id="room_alpha", role="grower"
        )


def test_overlapping_guest_request_ids_never_cross_deliver():
    broker = module.GuestRequestBroker()
    first = broker.prepare(
        message(request_id="same_id"), session_id="alice",
        room_id="room_alpha", role="grower", now=100.0
    )
    second = broker.prepare(
        message(path="/api/v1/rooms/room_beta/plants"),
        session_id="bob", room_id="room_beta", role="observer", now=100.0
    )
    assert first["request_id"] != second["request_id"]
    one = broker.route_reply(
        {"type": "read_result", "request_id": second["request_id"],
         "ok": True, "data": {"plants": []}}, now=101.0
    )
    assert one[0] == "bob"
    two = broker.route_reply(
        {"type": "read_result", "request_id": first["request_id"],
         "ok": True, "data": {"entries": []}}, now=101.0
    )
    assert two[0] == "alice"
    assert two[1]["request_id"] == "same_id"
    assert broker.pending_count == 0


def test_unsolicited_replies_and_mismatched_types_are_discarded():
    broker = module.GuestRequestBroker()
    req = broker.prepare(
        message(), session_id="guest",
        room_id="room_alpha", role="observer", now=0.0
    )
    assert broker.route_reply(
        {"type": "control_result", "request_id": req["request_id"]},
        now=1.0
    ) is None
    assert broker.route_reply(
        {"type": "read_result", "request_id": req["request_id"]},
        now=1.0
    ) is None
    assert broker.route_reply(
        {"type": "read_result", "request_id": "unknown"},
        now=1.0
    ) is None


def test_revocation_and_timeout_cancel_pending_responses():
    broker = module.GuestRequestBroker()
    req = broker.prepare(message(), session_id="guest",
                         room_id="room_alpha", role="observer", now=0.0)
    broker.revoke_session("guest")
    assert broker.route_reply(
        {"type": "read_result", "request_id": req["request_id"]},
        now=1.0
    ) is None
    req = broker.prepare(message(), session_id="guest",
                         room_id="room_alpha", role="observer", now=0.0)
    assert broker.route_reply(
        {"type": "read_result", "request_id": req["request_id"]},
        now=31.0
    ) is None


def test_pending_request_limit():
    broker = module.GuestRequestBroker()
    for _ in range(module.MAX_PENDING_PER_SESSION):
        broker.prepare(message(), session_id="alice",
                       room_id="room_alpha", role="grower", now=0.0)
    with pytest.raises(module.GuestRequestDenied):
        broker.prepare(message(), session_id="alice",
                       room_id="room_alpha", role="grower", now=0.0)
    assert broker.pending_count == module.MAX_PENDING_PER_SESSION
