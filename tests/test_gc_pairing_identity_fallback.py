import asyncio
from types import SimpleNamespace

import pytest

from app.devices import gc_pairing
from app.provisioning import usb_identity


class Provider:
    def __init__(self, result=None, error=None):
        self.result = result
        self.error = error

    async def prove_identity(self, device_id):
        if self.error:
            raise self.error
        return self.result


def test_fresh_identity_prefers_mqtt_proof():
    proof = SimpleNamespace(public_key="mqtt-key", body={})
    result, transport = asyncio.run(gc_pairing._fresh_identity_proof(Provider(result=proof), "gc-soil-123456", {"public_key": "mqtt-key"}))
    assert result is proof
    assert transport == "mqtt"


def test_fresh_identity_uses_verified_usb_fallback(monkeypatch):
    verified = usb_identity.UsbIdentityProof(
        device_id="gc-soil-123456",
        public_key="usb-key",
        fingerprint="a" * 64,
        hardware_uid="0011223344556677",
        firmware="0.5.1",
        calibration={"ready": True, "air_done": True, "wet_done": True},
    )
    monkeypatch.setattr(usb_identity, "prove_connected_device", lambda device_id: verified)
    expected = {"public_key": "usb-key", "fingerprint": "a" * 64}

    proof, transport = asyncio.run(gc_pairing._fresh_identity_proof(Provider(error=TimeoutError()), "gc-soil-123456", expected))

    assert transport == "usb"
    assert proof.public_key == "usb-key"
    assert proof.body["hardware_uid"] == "0011223344556677"
    assert proof.body["calibration"]["ready"] is True
    assert proof.body["state"]["meta"]["firmware"] == "0.5.1"


def test_usb_fallback_rejects_identity_mismatch(monkeypatch):
    verified = usb_identity.UsbIdentityProof(
        device_id="gc-soil-123456",
        public_key="different-key",
        fingerprint="b" * 64,
        hardware_uid="0011223344556677",
        firmware="0.5.1",
        calibration={"ready": True},
    )
    monkeypatch.setattr(usb_identity, "prove_connected_device", lambda device_id: verified)
    expected = {"public_key": "stored-key", "fingerprint": "a" * 64}

    with pytest.raises(PermissionError):
        asyncio.run(gc_pairing._fresh_identity_proof(Provider(error=TimeoutError()), "gc-soil-123456", expected))
