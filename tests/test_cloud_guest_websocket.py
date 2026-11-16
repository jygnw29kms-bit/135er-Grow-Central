"""Guest WebSocket scoped messages, revoked-session suppression, and no broadcast."""
import asyncio
import json
import sys
from pathlib import Path

from fastapi import HTTPException, WebSocketDisconnect
from sqlalchemy import create_engine, text

CLOUD_DIR = Path(__file__).resolve().parents[1] / "cloud/v7"
if str(CLOUD_DIR) not in sys.path:
    sys.path.insert(0, str(CLOUD_DIR))

from guest_websocket import CloudGuestRemote, GuestSocketState
from room_membership import ensure_schema

DEVICE = "device-test"
ROOM = "room_alpha"


def setup(tmp_path):
    engine = create_engine(f"sqlite:///{tmp_path / 'guest.db'}")
    with engine.begin() as db:
        db.execute(text("CREATE TABLE accounts(id TEXT PRIMARY KEY,status TEXT NOT NULL)"))
        db.execute(text("CREATE TABLE devices(id TEXT PRIMARY KEY,account_id TEXT,revoked_at INTEGER)"))
        for who in ("owner", "alice", "bob"):
            db.execute(text("INSERT INTO accounts(id,status) VALUES(:id,'active')"), {"id": who})
        db.execute(text("INSERT INTO devices(id,account_id,revoked_at) VALUES(:id,'owner',NULL)"),
                   {"id": DEVICE})
    ensure_schema(engine)
    with engine.begin() as db:
        for who,room,role in (("alice",ROOM,"grower"), ("bob","room_beta","observer")):
            db.execute(text("""INSERT INTO cloud_room_memberships
              (device_id,room_id,account_id,owner_account_id,role,joined_at,revoked_at)
              VALUES (:d,:r,:a,'owner',:role,10,NULL)"""),
              {"d": DEVICE, "r": room, "a": who, "role": role})
    return engine


class Socket:
    def __init__(self, incoming=()):
        self.incoming = list(incoming)
        self.outbound = []
        self.close_code = None
        self.accepted = False

    async def accept(self):
        self.accepted = True

    async def send_json(self, value):
        self.outbound.append(value)

    async def receive_text(self):
        if self.incoming:
            return self.incoming.pop(0)
        raise WebSocketDisconnect(code=1000)

    async def close(self, code):
        self.close_code = code


class DeviceSocket:
    def __init__(self):
        self.sent = []

    async def send_text(self, value):
        self.sent.append(json.loads(value))


def remote_for(engine, devices=None, auth=None):
    return CloudGuestRemote(
        engine=engine,
        account_from_access=auth or (lambda token: token),
        device_sockets=devices or {},
        socket_lock=asyncio.Lock(),
    )


def test_guest_read_forwarded_only_for_own_room(tmp_path):
    engine = setup(tmp_path)
    device = DeviceSocket()
    remote = remote_for(engine, {DEVICE: device})
    guest = Socket([
        json.dumps({"type":"auth","access_token":"alice","device_id":DEVICE,"room_id":ROOM}),
        json.dumps({"type":"read","request_id":"request1","path":f"/api/v1/rooms/{ROOM}/journal"}),
        json.dumps({"type":"read","request_id":"request2","path":"/api/v1/rooms/room_beta/journal"}),
        json.dumps({"type":"control","request_id":"request3","kind":"fan","action":"power","value":1}),
    ])
    asyncio.run(remote.connect(guest))
    assert guest.accepted
    assert guest.outbound[0]["guest_scoped"]
    assert guest.outbound[0]["role"] == "grower"
    assert len(device.sent) == 1
    assert device.sent[0]["type"] == "read"
    assert device.sent[0]["request_id"] != "request1"
    assert [x["error"] for x in guest.outbound[1:]] == [
        "guest_action_denied", "guest_action_denied"
    ]
    assert remote.broker.pending_count == 0


def test_invalid_account_and_wrong_room_close_before_forward(tmp_path):
    engine = setup(tmp_path)
    remote = remote_for(engine)
    invalid = Socket([json.dumps({
        "type":"auth","access_token":"alice","device_id":DEVICE,"room_id":"room_beta"
    })])
    asyncio.run(remote.connect(invalid))
    assert invalid.close_code == 4403
    def reject(_):
        raise HTTPException(401, "Expired")
    remote = remote_for(engine, auth=reject)
    expired = Socket([json.dumps({
        "type":"auth","access_token":"alice","device_id":DEVICE,"room_id":ROOM
    })])
    asyncio.run(remote.connect(expired))
    assert expired.close_code == 4401


def test_private_device_reply_not_sent_to_other_guest(tmp_path):
    engine = setup(tmp_path)
    remote = remote_for(engine)
    alice, bob = Socket(), Socket()
    remote.sessions["s1"] = GuestSocketState(alice, DEVICE, ROOM, "alice", "alice")
    remote.sessions["s2"] = GuestSocketState(bob, DEVICE, "room_beta", "bob", "bob")
    sent = remote.broker.prepare(
        {"type":"read","request_id":"alice_local","path":f"/api/v1/rooms/{ROOM}/journal"},
        session_id="s1",room_id=ROOM,role="grower"
    )
    handled = asyncio.run(remote.dispatch_device_result(DEVICE,json.dumps({
        "type":"read_result","request_id":sent["request_id"],"ok":True,
        "data":{"entries":[{"room_id":ROOM}]}
    })))
    assert handled is True
    assert alice.outbound[0]["request_id"] == "alice_local"
    assert bob.outbound == []


def test_revoked_guest_reply_consumed_without_broadcast(tmp_path):
    engine = setup(tmp_path)
    remote = remote_for(engine)
    alice = Socket()
    remote.sessions["s1"] = GuestSocketState(alice, DEVICE, ROOM, "alice", "alice")
    sent = remote.broker.prepare(
        {"type":"read","request_id":"one","path":f"/api/v1/rooms/{ROOM}/plants"},
        session_id="s1",room_id=ROOM,role="grower"
    )
    with engine.begin() as db:
        db.execute(text("""UPDATE cloud_room_memberships SET revoked_at=100
                           WHERE account_id='alice'"""))
    handled = asyncio.run(remote.dispatch_device_result(DEVICE,json.dumps({
        "type":"read_result","request_id":sent["request_id"],"ok":True,"data":{"plants":[]}
    })))
    assert handled is True
    assert alice.outbound == []


def test_invalid_type_reserved_reply_never_broadcast(tmp_path):
    engine = setup(tmp_path)
    remote = remote_for(engine)
    alice = Socket()
    remote.sessions["s1"] = GuestSocketState(alice, DEVICE, ROOM, "alice", "alice")
    sent = remote.broker.prepare(
        {"type":"read","request_id":"one","path":f"/api/v1/rooms/{ROOM}/plants"},
        session_id="s1",room_id=ROOM,role="grower"
    )
    handled = asyncio.run(remote.dispatch_device_result(DEVICE,json.dumps({
        "type":"control_result","request_id":sent["request_id"],"ok":True
    })))
    assert handled is True
    assert alice.outbound == []
    assert remote.broker.pending_count == 0


def test_late_or_revoked_guest_reply_never_reaches_owner_broadcast(tmp_path):
    engine = setup(tmp_path)
    remote = remote_for(engine)
    alice = Socket()
    remote.sessions["s1"] = GuestSocketState(alice, DEVICE, ROOM, "alice", "alice")
    sent = remote.broker.prepare(
        {"type": "read", "request_id": "late", "path": f"/api/v1/rooms/{ROOM}/plants"},
        session_id="s1", room_id=ROOM, role="grower",
    )
    internal_id = sent["request_id"]
    assert internal_id.startswith("gc_guest_")
    remote.broker.revoke_session("s1")
    remote.sessions.pop("s1")
    # Even after revocation, the delayed response must be consumed privately.
    handled = asyncio.run(remote.dispatch_device_result(DEVICE, json.dumps({
        "type": "read_result", "request_id": internal_id, "ok": True,
        "data": {"plants": [{"room_id": ROOM, "name": "private"}]},
    })))
    assert handled is True
    assert alice.outbound == []
    # Ordinary owner responses retain their existing forwarding behavior.
    assert asyncio.run(remote.dispatch_device_result(DEVICE, json.dumps({
        "type": "read_result", "request_id": "owner_read_1", "ok": True,
    }))) is False
