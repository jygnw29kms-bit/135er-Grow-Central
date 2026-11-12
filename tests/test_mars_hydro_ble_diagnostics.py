"""Mars Hydro FC3000 / DF150-M: no guessed GATT writes, only bounded read diagnostics."""
from __future__ import annotations

from types import SimpleNamespace
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app import mars_hydro_ble as mh


class FakeChar:
    def __init__(self, uuid, properties):
        self.uuid = uuid
        self.handle = 4
        self.properties = properties


class FakeGatt:
    uuid = "12345678-0000-1000-8000-00805f9b34fb"
    characteristics = [
        FakeChar("12340000-0000-1000-8000-00805f9b34fb", ["read"]),
        FakeChar("12340001-0000-1000-8000-00805f9b34fb", ["notify"]),
        FakeChar("12340002-0000-1000-8000-00805f9b34fb", ["write"]),
    ]


class FakeClient:
    calls = []
    def __init__(self, address, timeout=12.0):
        assert address == "AA:BB:CC"
        self.services = [FakeGatt()]
        self.callback = None

    async def __aenter__(self):
        return self

    async def __aexit__(self, *exc):
        return None

    async def read_gatt_char(self, uuid):
        self.calls.append(("read", uuid))
        return bytearray(b"OK")

    async def start_notify(self, uuid, callback):
        self.calls.append(("subscribe", uuid))
        self.callback = callback
        callback(SimpleNamespace(uuid=uuid), bytearray.fromhex("02 41 50"))

    async def stop_notify(self, uuid):
        self.calls.append(("unsubscribe", uuid))

    async def write_gatt_char(self, *args, **kwargs):
        pytest.fail("Mars diagnostic MUST NOT perform GATT writes")


class FakeScanner:
    @staticmethod
    async def discover(timeout=5.0, return_adv=False):
        assert return_adv is True
        device = SimpleNamespace(name="MARS FC3000")
        adv = SimpleNamespace(
            local_name="MARS FC3000", rssi=-43,
            service_uuids=["12345678-0000-1000-8000-00805f9b34fb"],
            manufacturer_data={1234: b"\x01"},
        )
        return {"AA:BB:CC": (device, adv)}


@pytest.fixture
def client(monkeypatch):
    mh._candidates.clear()
    FakeClient.calls = []
    monkeypatch.setattr(mh, "BleakScanner", FakeScanner)
    monkeypatch.setattr(mh, "BleakClient", FakeClient)
    app = FastAPI()
    app.include_router(mh.router)
    app.dependency_overrides[mh.require_write_auth] = lambda: None
    return TestClient(app)


def test_scan_inspect_and_observe_do_not_write(client):
    status = client.get("/api/mars-hydro/ble/status")
    assert status.status_code == 200
    assert status.json()["control"] == "blocked_pending_model_specific_validation"

    scan = client.post("/api/mars-hydro/ble/scan")
    assert scan.status_code == 200
    device = scan.json()["devices"][0]
    assert device["mars_hydro_hint"] is True
    assert device["identity_verified"] is False
    candidate_id = device["candidate_id"]

    report = client.post("/api/mars-hydro/ble/inspect", json={"candidate_id": candidate_id})
    assert report.status_code == 200, report.text
    assert report.json()["reads"][0]["value"]["text"] == "OK"
    assert report.json()["write_attempted"] is False
    assert report.json()["protocol_validated"] is False

    uuid = FakeGatt.characteristics[1].uuid
    observe = client.post("/api/mars-hydro/ble/observe", json={
        "candidate_id": candidate_id, "characteristic_uuid": uuid, "seconds": 0.5
    })
    assert observe.status_code == 200, observe.text
    assert observe.json()["event_count"] == 1
    assert observe.json()["events"][0]["value"]["hex"] == "02 41 50"
    assert observe.json()["write_attempted"] is False
    assert ("subscribe", uuid) in FakeClient.calls
    assert ("unsubscribe", uuid) in FakeClient.calls

    block = client.post("/api/mars-hydro/ble/control-test")
    assert block.status_code == 403
    assert not any(call[0] == "write" for call in FakeClient.calls)


def test_unscanned_device_and_non_notify_uuid_are_denied(client):
    unknown = "0" * 20
    assert client.post("/api/mars-hydro/ble/inspect", json={"candidate_id": unknown}).status_code == 409
    candidate = client.post("/api/mars-hydro/ble/scan").json()["devices"][0]["candidate_id"]
    not_notify = FakeGatt.characteristics[2].uuid
    response = client.post("/api/mars-hydro/ble/observe", json={
        "candidate_id": candidate, "characteristic_uuid": not_notify,
    })
    assert response.status_code == 422
    assert FakeClient.calls == []


def test_ble_endpoints_are_auth_protected():
    app = FastAPI()
    app.include_router(mh.router)
    # This check requires a write-authorized, logged-in operator, not a public
    # read-only status API.
    assert all(len(route.dependencies) >= 1 for route in mh.router.routes)


def test_payload_is_bounded_and_not_interpreted_as_power_or_speed():
    result = mh._payload(b"A" * 300)
    assert result["truncated"] is True
    assert result["length"] == 300
    assert "speed" not in result and "brightness" not in result
    assert len(result["text"]) == 128
